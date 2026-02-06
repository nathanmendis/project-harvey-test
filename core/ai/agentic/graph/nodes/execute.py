import time
import json
import logging
from langchain_core.messages import ToolMessage, AIMessage
from ..tools_registry import tool_registry
from .utils import get_state_value, append_trace, set_state_value, get_user

logger = logging.getLogger("harvey")

def should_execute(state):
    pending = get_state_value(state, "pending_tool")
    requires_approval = get_state_value(state, "requires_approval", False)
    return bool(pending) and not requires_approval

def execute_node(state):
    call = get_state_value(state, "pending_tool")
    if not call:
        return {}
    
    draft = get_state_value(state, "draft_email")
    if call["name"] == "send_email_tool" and draft:
        call["args"] = {
            "recipient_email": draft["recipient"],
            "subject": draft["subject"],
            "body": draft["body"],
        }
        set_state_value(state, "draft_email", None)

    func = tool_registry.get(call["name"])
    user = get_user(state)
    args = call["args"]

    start = time.time()
    try:
        logger.info(f"Executing tool: {call['name']}")
        if "user" in args:
            del args["user"]

        result = func(user=user, **args)
        parsed = json.loads(result)
        message = parsed.get("message", result)

        append_trace(state, {
            "node": "TOOL",
            "tool": call["name"],
            "duration_ms": int((time.time() - start) * 1000),
            "link": parsed.get("link")
        })

        set_state_value(state, "pending_tool", None)
        return {
            "messages": [ToolMessage(tool_call_id=call["id"], content=message)],
            "pending_tool": None,
            "requires_approval": False
        }

    except Exception as e:
        logger.error(f"Tool execution failed: {e}")
        set_state_value(state, "pending_tool", None)
        return {
            "messages": [AIMessage(content=f"Tool failed: {e}")],
            "pending_tool": None,
            "requires_approval": False
        }
