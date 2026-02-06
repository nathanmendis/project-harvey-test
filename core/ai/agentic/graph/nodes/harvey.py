import time
import json
import logging
import pytz
from django.utils import timezone
from langchain_core.messages import SystemMessage, AIMessage, HumanMessage, ToolMessage
from ..tools_registry import AVAILABLE_TOOLS, get_router_llm, get_reasoner_llm
from ..harvey_prompt import STATIC_SYSTEM_PROMPT, DYNAMIC_PROMPT
from .utils import get_state_value, append_trace, set_state_value

logger = logging.getLogger("harvey")

def harvey_node(state):
    messages = get_state_value(state, "messages", [])
    intent = get_state_value(state, "intent", "chat")

    if messages and isinstance(messages[-1], ToolMessage):
        logger.info("[INFO] Harvey Node: Bypassing LLM")
        return {}

    if intent == "chat":
        llm = get_router_llm()
        logger.info("[INFO] Harvey Node: Using 8B Model (Chat Mode)")
    else:
        llm = get_reasoner_llm()
        logger.info("[INFO] Harvey Node: Using 70B Model (Tool Mode)")

    context = get_state_value(state, "context", {})
    current_goal = context.get("current_goal", "None")
    last_active_topic = context.get("last_active_topic", "None")
    
    # TOKEN OPTIMIZED: Flattened extracted_info
    info_dict = context.get("extracted_info", {})
    extracted_info = "\n".join(f"- {k}: {v}" for k, v in info_dict.items()) if info_dict else "None"

    tools_str = (
        "No tools available."
        if intent == "chat"
        else "\n".join(f"- {t.name}: {t.description}" for t in AVAILABLE_TOOLS)
    )

    now_ist = timezone.now().astimezone(pytz.timezone("Asia/Kolkata"))
    current_date_text = now_ist.strftime("%A, %B %d, %Y, %I:%M %p")

    target_tool_hint = ""
    target_tool = get_state_value(state, "target_tool")
    if intent == "tool" and target_tool:
        target_tool_hint = f"\nROUTER HINT: Use '{target_tool}'."

    sys = (
        STATIC_SYSTEM_PROMPT
        + DYNAMIC_PROMPT.format(
            current_goal=current_goal,
            current_date=current_date_text,
            last_active_topic=last_active_topic,
            extracted_info=extracted_info,
            tools=tools_str,
        )
        + target_tool_hint
    )

    if intent == "chat":
        sys += "\n\nMODE: CHAT. No tool use. If asked to draft, generate draft only."

    history_size = 6 if intent == "tool" else 4
    history = messages[-history_size:]
    msgs = [SystemMessage(content=sys)] + history

    start = time.time()
    try:
        if intent == "tool":
            result = llm.bind_tools(AVAILABLE_TOOLS).invoke(msgs)
        else:
            result = llm.invoke(msgs)

        from .utils import log_token_usage
        model_label = f"Harvey ({'70B' if intent == 'tool' else '8B'})"
        log_token_usage(result, model_label)

        append_trace(state, {
            "node": "HARVEY",
            "duration_ms": int((time.time() - start) * 1000),
            "tool_call": bool(result.tool_calls),
        })

        if result.tool_calls:
            tool_call = result.tool_calls[0]
            tool_name = tool_call["name"]
            user_text = "".join(m.content.lower() for m in messages if isinstance(m, HumanMessage))

            if tool_name == "send_email_tool" and "draft" in user_text:
                set_state_value(state, "draft_email", {
                    "recipient": tool_call["args"].get("recipient_email"),
                    "subject": tool_call["args"].get("subject"),
                    "body": result.content.strip(),
                })

            logger.info(f"Harvey decided to use tool: {tool_name}")
            return {"messages": [result], "pending_tool": tool_call, "requires_approval": False}

        return {"messages": [result]}

    except Exception as e:
        logger.error(f"Harvey thought error: {e}")
        return {"messages": [AIMessage(content="Thought error. Try again.")]}
