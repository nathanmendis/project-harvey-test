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
    llm = get_reasoner_llm() # 70B Model
    
    context = get_state_value(state, "context", {})
    messages = get_state_value(state, "messages", [])
    
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
                 return {"messages": [AIMessage(content="❌ Action cancelled. What would you like to do instead?")], 
                         "pending_tool": None, "requires_approval": False}

    current_goal = context.get("current_goal", "None")
    last_active_topic = context.get("last_active_topic", "None")
    extracted_info = json.dumps(context.get("extracted_info", {}), indent=2)
    tools = "\n".join(f"- {t.name}: {t.description}" for t in AVAILABLE_TOOLS)

    current_date = datetime.datetime.now().strftime("%A, %B %d, %Y")

    sys = SYSTEM_PROMPT.format(
        current_goal=current_goal, 
        current_date=current_date,
        last_active_topic=last_active_topic,
        extracted_info=extracted_info,
        tools=tools
    )
    
    history = messages[-10:]
    while history and not isinstance(history[0], HumanMessage):
        history.pop(0)

    msgs = [SystemMessage(content=sys)] + history

    # --- ROUTING LOGIC ---
    intent = get_state_value(state, "intent", "chat")
    target_tool = get_state_value(state, "target_tool", None)
    
    start = time.time()
    try:
        logger.debug(f"Harvey (70B) executing with Intent: {intent}")
        
        if intent == "tool":
            # 70B drafts the tool input
            # We bind ALL tools so it can pick the schema, but we expect it to use target_tool
            # Optimization: We COULD bind only the specific tool if we trust the router 100%
            # For now, binding all is safer if Router matched vaguely.
            result = llm.bind_tools(AVAILABLE_TOOLS).invoke(msgs)
        else:
             # Chat mode: NO tools bound. 
             # preventing 70B from hallucinating tool usage.
             result = llm.invoke(msgs)

        append_trace(state, {
            "node": "HARVEY",
            "duration_ms": int((time.time() - start) * 1000),
            "tool_call": bool(result.tool_calls),
        })

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
        return {"messages": [AIMessage(content="⚠️ Thought error. Try again.")]}
    

def should_execute(state):
    pending = get_state_value(state, "pending_tool")
    requires_approval = get_state_value(state, "requires_approval", False)
    
    logger.debug(f"should_execute check: pending={bool(pending)}, approval={requires_approval}")

    if requires_approval:
        return False
        
    return bool(pending)


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
        
        # Ensure the LLM sees the link if one was returned
        if parsed.get("link"):
            message += f"\nLink: {parsed['link']}"

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

    updates = {}
    
    # Only clear pending_tool if we are NOT waiting for approval
    # If we are waiting for approval, we need to keep it for the next turn
    requires_approval = get_state_value(state, "requires_approval", False)
    if not requires_approval:
        updates["pending_tool"] = None

    if new_context:
        updates["context"] = new_context
    
    return updates