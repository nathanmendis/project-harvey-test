import json
import logging
from django.utils import timezone
from pydantic import BaseModel
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from django.core.cache import cache
from google.api_core.exceptions import ResourceExhausted

from .graph import graph
from core.models.chatbot import Conversation, Message, GraphRun
from .tools_registry import tool_registry

logger = logging.getLogger("harvey")

class LLMResponse(BaseModel):
    response: str
    conversation_id: int
    title: str


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


def generate_llm_reply(prompt: str, user, conversation_id=None, request=None):
    # 1. Check for Rate Limit Block
    if cache.get(f"chat_block_{user.id}"):
        return LLMResponse(response=" System is cooling down due to high traffic. Please try again in 60 seconds.", conversation_id=0, title="Error")

    if conversation_id:
        try:
            convo = Conversation.objects.get(id=conversation_id, user=user)
        except Conversation.DoesNotExist:
            return LLMResponse(response=" Conversation not found.", conversation_id=0, title="Error")
    else:
        # Create NEW conversation
        # Generate a title based on the first few words of the prompt
        title = " ".join(prompt.split()[:4]) + "..." if prompt else "New Chat"
        convo = Conversation.objects.create(
            organization=user.organization,
            user=user,
            title=title,
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

    # Summary logging instead of full dump to avoid Unicode errors and massive logs
    logger.debug(f"Graph invoke. User: {user.username}, Msg Count: {len(state_input.get('messages', []))}")

    try:
        result = graph.invoke(state_input, config=config)
        # Reduce log verbosity: only show keys and last message preview
        msgs = result.get("messages", [])
        last_msg = msgs[-1].content[:50] + "..." if msgs else "No messages"
        logger.debug(f"Graph completed. Keys: {list(result.keys())}, Last output: {last_msg}")

        pending_tool = result.get("pending_tool")
        final_text = ""

        if pending_tool:
            tool_name = pending_tool.get("name")
            tool_args = pending_tool.get("args", {})
            tool_func = tool_registry.get(tool_name)

            logger.info(f"Running Tool: {tool_name}")
            if tool_func:
                tool_args["user"] = user
                try:
                    raw = tool_func(**tool_args)
                    data = json.loads(raw)
                    tool_msg = data.get("message", "Action completed.")
                    # Append tool result to messages for history
                    result["messages"].append(ToolMessage(tool_call_id=pending_tool["id"], content=tool_msg))
                    result["pending_tool"] = None
                except Exception as e:
                    logger.error(f"Tool execution failed: {e}")
                    result["messages"].append(AIMessage(content=f"⚠️ Tool failed: {e}"))
            else:
                result["messages"].append(AIMessage(content=f"⚠️ Unknown tool '{tool_name}'"))

        # --- FINAL AGGREGATION ---
        # Combine all NEW messages from this turn (AI or Tool) into a final transcript
        new_msgs = result.get("messages", [])[len(state_input.get("messages", [])):]
        
        parts = []
        for msg in new_msgs:
            if isinstance(msg, (AIMessage, ToolMessage)):
                txt = _content_to_text(msg.content)
                if txt:
                     parts.append(txt)
        
        if parts:
            final_text = "\n\n".join(parts)
        else:
            final_text = "Action completed."

        # Save DB run metadata
        run.status = "success"
        run.output_text = final_text
        run.trace = result.get("trace", [])
        run.finished_at = timezone.now()
        run.save()

        # Save chat history
        _save_chat(convo, user, prompt, final_text)

        return LLMResponse(
            response=final_text,
            conversation_id=convo.id,
            title=convo.title
        )

    except ResourceExhausted:
        logger.warning(f"Rate Limit Hit for user {user.id}")
        # Block user for 60 seconds
        cache.set(f"chat_block_{user.id}", True, timeout=60)
        
        run.status = "error"
        run.error_message = "Rate Limit Exceeded (429)"
        run.save()
        
        return LLMResponse(
            response=" API Rate limit reached. System is cooling down. Please wait 60 seconds.",
            conversation_id=convo.id if locals().get('convo') else 0,
            title="Error"
        )

    except Exception as e:
        logger.error(f"Graph ERROR: {repr(e)}", exc_info=True)

        run.status = "error"
        run.error_message = str(e)
        run.finished_at = timezone.now()
        try:
            run.save()
        except Exception as db_err:
            logger.error(f"Failed to update GraphRun status: {db_err}")

        return LLMResponse(
            response="⚠️ Something went wrong. Try again!",
            conversation_id=convo.id if locals().get('convo') else 0,
            title="Error"
        )
