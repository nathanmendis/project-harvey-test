
import json
from django.utils import timezone
from pydantic import BaseModel
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.runnables import RunnableConfig

from .graph import graph
from core.models.chatbot import Conversation, Message, GraphRun
from .tools_registry import tool_registry


class LLMResponse(BaseModel):
    response: str


def _content_to_text(content):
    """Normalize AI content → plain string."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            c.get("text", "")
            for c in content
            if isinstance(c, dict) and c.get("type") == "text"
        ).strip()
    return str(content)


def _save_chat(convo, user, user_input, ai_output):
    Message.objects.create(
        sender="user",
        message_text=user_input,
        conversation=convo,
        organization=user.organization,
    )
    Message.objects.create(
        sender="ai",
        message_text=ai_output,
        conversation=convo,
        organization=user.organization,
    )


def generate_llm_reply(prompt: str, user, request=None):
    convo, _ = Conversation.objects.get_or_create(
        organization=user.organization,
        user=user,
        defaults={"title": "Chat Session"},
    )

    run = GraphRun.objects.create(
        conversation=convo,
        user=user,
        input_text=prompt,
        status="running",
    )

    thread_id = f"convo-{convo.id}"

    config = RunnableConfig(
        configurable={"thread_id": thread_id},
        metadata={"graph_run_id": str(run.id)},
    )

    checkpoint = graph.get_state(config=config)
    prev_state = checkpoint.values if checkpoint else {}

    prev_msgs = prev_state.get("messages", [])[-10:]

    state_input = {
        "messages": prev_msgs + [HumanMessage(content=prompt)],
        "user_id": user.id,
        "summary": prev_state.get("summary"),
        "pending_tool": prev_state.get("pending_tool"),
        "trace": prev_state.get("trace", []),
    }

    print("🚀 Graph invoke →", state_input)

    try:
        result = graph.invoke(state_input, config=config)
        print("🟢 Graph completed →", result)

        pending_tool = result.get("pending_tool")
        final_text = ""

        if pending_tool:
            tool_name = pending_tool.get("name")
            tool_args = pending_tool.get("args", {})
            tool_func = tool_registry.get(tool_name)

            print(f"🛠 Running Tool → {tool_name} - Args: {tool_args}")

            if not tool_func:
                final_text = f"⚠️ Unknown tool '{tool_name}'"
                result["pending_tool"] = pending_tool  # still unresolved
            else:
                tool_args["user"] = user

                try:
                    raw = tool_func(**tool_args)
                    data = json.loads(raw)

                    if data.get("ok"):
                        final_text = data.get("message", "Action completed.")
                        result["pending_tool"] = None  # resolved ✔
                    else:
                        final_text = data.get("message", "I still need details.")
                        result["pending_tool"] = pending_tool  # still pending ❗

                except Exception as e:
                    final_text = f"⚠️ Tool failed: {str(e)}"
                    result["pending_tool"] = pending_tool  # still pending ❌

            result["messages"].append(AIMessage(content=final_text))

        else:
            last = result["messages"][-1]
            final_text = _content_to_text(last.content)

        # Save DB run metadata
        run.status = "success"
        run.output_text = final_text
        run.trace = result.get("trace", [])
        run.finished_at = timezone.now()
        run.save()

        # Save chat history
        _save_chat(convo, user, prompt, final_text)

        return LLMResponse(response=final_text)

    except Exception as e:
        print("🔥 Graph ERROR:", repr(e))
        import traceback; traceback.print_exc()

        run.status = "error"
        run.error_message = str(e)
        run.finished_at = timezone.now()
        run.save()

        return LLMResponse(response="⚠️ Something went wrong. Try again!")
