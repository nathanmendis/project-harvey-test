from langchain_core.messages import SystemMessage, ToolMessage, AIMessage, HumanMessage
from .tools_registry import AVAILABLE_TOOLS, tool_registry, get_router_llm, get_reasoner_llm
from .harvey_prompt import SYSTEM_PROMPT
from .summarizer import summarize
from django.contrib.auth import get_user_model
import json, time
import datetime
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
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field

# Define Router Output Schema
class RouterOutput(BaseModel):
    intent: str = Field(description="One of 'tool' or 'chat'")
    tool_name: str = Field(description="Name of the tool to use, or 'None' if chat", default="None")

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



SENSITIVE_TOOLS = {"send_email_tool", "create_calendar_event_tool"}

def router_node(state):
    """
    Uses Llama-3-8B to classify user intent.
    Output: Updates 'intent' and 'target_tool' in state.
    """
    messages = get_state_value(state, "messages", [])
    if not messages:
        return {}

    # Get last message
    last_msg = messages[-1]
    if not isinstance(last_msg, HumanMessage):
        # If not human, assume we continue flow or just chat
        return {"intent": "chat", "target_tool": None}

    llm = get_router_llm()
    
    # Simple tool definitions for the router
    tools_desc = "\n".join(f"- {t.name}: {t.description}" for t in AVAILABLE_TOOLS)
    
    router_prompt = f"""
    You are an intent classifier. Analyze the user's request and decide if a tool is needed or if it's a general conversation.
    
    AVAILABLE TOOLS:
    {tools_desc}
    
    RULES:
    1. If the user asks to perform an action (email, calendar, search database, schedule interview), choose 'tool'.
    2. If the user says hello, asks general questions, or thanks you, choose 'chat'.
    3. Return JSON: {{ "intent": "tool" or "chat", "tool_name": "<name>" }}
    
    USER QUERY:
    {last_msg.content}
    """
    
    parser = JsonOutputParser(pydantic_object=RouterOutput)
    
    try:
        logger.info("Router (8B) analyzing...")
        start = time.time()
        
        # We use a simple chain
        chain = llm | parser
        result = chain.invoke(router_prompt)
        
        duration = int((time.time() - start) * 1000)
        logger.info(f"Router Decision: {result} ({duration}ms)")
        
        append_trace(state, {
            "node": "ROUTER",
            "intent": result["intent"],
            "tool": result.get("tool_name"),
            "duration_ms": duration
        })

        return {"intent": result["intent"], "target_tool": result.get("tool_name")}

    except Exception as e:
        logger.error(f"Router failed: {e}")
        # Fallback to safe "chat"
        return {"intent": "chat", "target_tool": None}


def harvey_node(state):
    messages = get_state_value(state, "messages", [])
    intent = get_state_value(state, "intent", "chat")
    
    # If the last message was a Tool execution, we BYPASS the LLM and return the result directly.
    # This ensures links and details are preserved exactly as the tool returned them.
    if messages and isinstance(messages[-1], ToolMessage):
        logger.info("[INFO] Harvey Node: Bypassing LLM (Returning Tool Output Directly)")
        tool_output = messages[-1].content
        return {"messages": [AIMessage(content=tool_output)]}

    # --- MODEL SELECTION STRATEGY ---
    if intent == "chat":
        llm = get_router_llm() # 8B Model for Chat
        logger.info("[INFO] Harvey Node: Using 8B Model (Chat Mode)")
    else:
        llm = get_reasoner_llm() # 70B Model for Tools
        logger.info("[INFO] Harvey Node: Using 70B Model (Tool Mode)")
    
    context = get_state_value(state, "context", {})
    
    # --- Human-in-the-Loop Check (Existing Logic) ---
    requires_approval = get_state_value(state, "requires_approval", False)
    pending_tool = get_state_value(state, "pending_tool", None)

    if requires_approval and pending_tool:
        last_msg = messages[-1]
        if isinstance(last_msg, HumanMessage):
             user_text = last_msg.content.lower().strip()
             if any(w in user_text for w in CONFIRM):
                 logger.info("User confirmed sensitive action.")
                 set_state_value(state, "requires_approval", False)
                 return {"pending_tool": pending_tool, "requires_approval": False}
             else:
                 logger.info("User rejected or digressed.")
                 set_state_value(state, "requires_approval", False)
                 set_state_value(state, "pending_tool", None)
                 return {"messages": [AIMessage(content="Action cancelled. What would you like to do instead?")], 
                         "pending_tool": None, "requires_approval": False}

    current_goal = context.get("current_goal", "None")
    last_active_topic = context.get("last_active_topic", "None")
    extracted_info = json.dumps(context.get("extracted_info", {}), indent=2)
    if intent == "chat":
        tools_str = "No tools available in Chat Mode."
    else:
        tools_str = "\n".join(f"- {t.name}: {t.description}" for t in AVAILABLE_TOOLS)

    # Add User Timezone Context (Hardcoded to IST for now as per user location)
    # Ideally this comes from user profile.
    user_timezone = "IST (UTC+05:30)"
    
    current_date = datetime.datetime.now().strftime("%A, %B %d, %Y, %I:%M %p")

    sys = SYSTEM_PROMPT.format(
        current_goal=current_goal, 
        current_date=f"{current_date} {user_timezone}",
        last_active_topic=last_active_topic,
        extracted_info=extracted_info,
        tools=tools_str
    )
    
    # Add explicit instruction for Chat mode to prevent hallucinations
    if intent == "chat":
        sys += "\n\nMODE: CHAT. You have NO tools. Do not pretend to execute actions. Just answer the user."

    history = messages[-10:]
    while history and not isinstance(history[0], HumanMessage):
        history.pop(0)

    msgs = [SystemMessage(content=sys)] + history

    target_tool = get_state_value(state, "target_tool", None)
    
    start = time.time()
    try:
        logger.debug(f"Harvey executing with Intent: {intent}")
        
        if intent == "tool":
            # 70B drafts the tool input
            result = llm.bind_tools(AVAILABLE_TOOLS).invoke(msgs)
        else:
             # Chat mode: 8B model, NO tools bound.
             result = llm.invoke(msgs)
             


        append_trace(state, {
            "node": "HARVEY",
            "duration_ms": int((time.time() - start) * 1000),
            "tool_call": bool(result.tool_calls),
        })

        # --- LOG TOKEN USAGE ---
        if hasattr(result, "response_metadata"):
            usage = result.response_metadata.get("token_usage", {})
            logger.info(f"[INFO] Token Usage: {usage}")

        if result.tool_calls:
            tool_call = result.tool_calls[0]
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]

            # --- SENSITIVE TOOL INTERCEPTION ---
            if tool_name in SENSITIVE_TOOLS:
                logger.info(f"Intercepting sensitive tool: {tool_name}")
                set_state_value(state, "pending_tool", tool_call)
                set_state_value(state, "requires_approval", True)
                
                draft_msg = f"I've prepared the following action:\n\n**Tool**: `{tool_name}`\n"
                for k, v in tool_args.items():
                    if k != "user":
                        draft_msg += f"- **{k}**: {v}\n"
                
                draft_msg += "\nDo you want me to proceed? (Type 'Confirm' or 'Yes')"
                
                return {"messages": [AIMessage(content=draft_msg)], "pending_tool": tool_call, "requires_approval": True}

            logger.info(f"Harvey decided to use tool: {tool_name}")
            set_state_value(state, "pending_tool", tool_call)
            return {"messages": [result], "pending_tool": tool_call, "requires_approval": False}

        return {"messages": [result]}

    except Exception as e:
        logger.error(f"Harvey thought error: {e}")
        append_trace(state, {"node": "HARVEY", "error": str(e)})
        return {"messages": [AIMessage(content="Thought error. Try again.")]}
    

def should_execute(state):
    pending = get_state_value(state, "pending_tool")
    requires_approval = get_state_value(state, "requires_approval", False)
    
    logger.debug(f"should_execute check: pending={bool(pending)}, approval={requires_approval}")

    if requires_approval:
        return False
        
    return bool(pending)


def get_user(state):
    """Retrieve user object from state using user_id"""
    user_id = get_state_value(state, "user_id")
    if user_id:
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            logger.error(f"User with id {user_id} not found.")
            return None
    return None


def execute_node(state):
    call = get_state_value(state, "pending_tool")
    func = tool_registry.get(call["name"])
    user = get_user(state)
    args = call["args"]

    start = time.time()
    try:
        logger.info(f"Executing tool: {call['name']} with args: {args}")
        
        # Fix: Remove 'user' from args if the LLM provided it (usually as None)
        # to avoid "multiple values for keyword argument" error.
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
        logger.info(f"Tool execution successful: {message}")
        return {"messages": [ToolMessage(tool_call_id=call["id"], content=message)], "pending_tool": None}

    except Exception as e:
        logger.error(f"Tool execution failed: {e}")
        append_trace(state, {"node": "TOOL", "tool": call["name"], "error": str(e)})
        set_state_value(state, "pending_tool", None)
        return {"messages": [AIMessage(content=f" Tool failed: {e}")], "pending_tool": None}


def summary_node(state):
    messages = get_state_value(state, "messages", [])
    new_context = summarize(messages)

    # 🔍 Debug log summary
    logger.debug(f"Updated Context: {new_context}")

    updates = {}
    
    # Only clear pending_tool if we are NOT waiting for approval
    # If we are waiting for approval, we need to keep it for the next turn
    requires_approval = get_state_value(state, "requires_approval", False)
    if not requires_approval:
        updates["pending_tool"] = None
        # Safety net: Ensure approval is False if we are clearing tool
        updates["requires_approval"] = False

    if new_context:
        updates["context"] = new_context
    
    return updates