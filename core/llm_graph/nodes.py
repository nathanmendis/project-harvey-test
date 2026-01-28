from langchain_core.messages import SystemMessage, ToolMessage, AIMessage, HumanMessage
from .tools_registry import AVAILABLE_TOOLS, tool_registry, get_llm
from .harvey_prompt import SYSTEM_PROMPT
from .summarizer import summarize
from django.contrib.auth import get_user_model
import json, time
import logging

logger = logging.getLogger("harvey")

User = get_user_model()

CONFIRM = {"yes", "ok", "okay", "sure", "confirm", "send it", "go ahead", "yup"}

def _content_to_plaintext(msg):
    content = msg.content
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            c.get("text", "")
            for c in content
            if isinstance(c, dict) and c.get("type") == "text"
        )
    return str(content)

def get_state_value(state, key, default=None):
    """Work for both HarveyState objects and plain dicts"""
    if hasattr(state, key):
        return getattr(state, key, default)
    return state.get(key, default)


def set_state_value(state, key, value):
    """Update value no matter the state type"""
    if hasattr(state, key):
        setattr(state, key, value)
    else:
        state[key] = value


def append_trace(state, entry):
    trace = get_state_value(state, "trace", [])
    trace.append(entry)
    set_state_value(state, "trace", trace)


def get_user(state):
    uid = get_state_value(state, "user_id")
    if not uid:
        return None
    try:
        return User.objects.get(id=uid)
    except:
        return None


def harvey_node(state):
    llm = get_llm()
    tools = "\n".join(f"- {t.name}: {t.description}" for t in AVAILABLE_TOOLS)

    context = get_state_value(state, "context", {})
    
    current_goal = context.get("current_goal", "None")
    last_active_topic = context.get("last_active_topic", "None")
    extracted_info = json.dumps(context.get("extracted_info", {}), indent=2)

    messages = get_state_value(state, "messages", [])

    sys = SYSTEM_PROMPT.format(
        current_goal=current_goal, 
        last_active_topic=last_active_topic,
        extracted_info=extracted_info,
        tools=tools
    )
    # Limit history to prevent payload explosion (keep last 10 messages)
    history = messages[-10:]
    
    # Gemeni API requires that the conversation starts with a User message (after System)
    # If the slice starts with AI, remove it.
    while history and not isinstance(history[0], HumanMessage):
        history.pop(0)

    msgs = [SystemMessage(content=sys)] + history

    start = time.time()
    try:
        logger.debug(f"Harvey is thinking... (Goal: {current_goal})")
        result = llm.bind_tools(AVAILABLE_TOOLS).invoke(msgs)

        append_trace(state, {
            "node": "HARVEY",
            "duration_ms": int((time.time() - start) * 1000),
            "tool_call": bool(result.tool_calls),
        })

        if result.tool_calls:
            tool_call = result.tool_calls[0]
            logger.info(f"Harvey decided to use tool: {tool_call['name']}")
            set_state_value(state, "pending_tool", tool_call)
            return {"messages": [result], "pending_tool": tool_call}

        return {"messages": [result]}

    except Exception as e:
        logger.error(f"Harvey thought error: {e}")
        append_trace(state, {"node": "HARVEY", "error": str(e)})
        return {"messages": [AIMessage(content="⚠️ Thought error. Try again.")]}
    

def should_execute(state):
    pending = get_state_value(state, "pending_tool")
    return bool(pending)


def execute_node(state):
    call = get_state_value(state, "pending_tool")
    func = tool_registry.get(call["name"])
    user = get_user(state)
    args = call["args"]

    start = time.time()
    try:
        logger.info(f"Executing tool: {call['name']} with args: {args}")
        result = func(user=user, **args)
        parsed = json.loads(result)
        message = parsed.get("message", result)

        append_trace(state, {
            "node": "TOOL",
            "tool": call["name"],
            "duration_ms": int((time.time() - start) * 1000),
        })

        set_state_value(state, "pending_tool", None)
        logger.info(f"Tool execution successful: {message}")
        return {"messages": [ToolMessage(tool_call_id=call["id"], content=message)], "pending_tool": None}

    except Exception as e:
        logger.error(f"Tool execution failed: {e}")
        append_trace(state, {"node": "TOOL", "tool": call["name"], "error": str(e)})
        set_state_value(state, "pending_tool", None)
        return {"messages": [AIMessage(content=f"⚠️ Tool failed: {e}")], "pending_tool": None}


def summary_node(state):
    messages = get_state_value(state, "messages", [])
    new_context = summarize(messages)

    # 🔍 Debug log summary
    logger.debug(f"Updated Context: {new_context}")

    updates = {"pending_tool": None}  # Always clear pending tool at end of turn
    if new_context:
        updates["context"] = new_context
    
    return updates