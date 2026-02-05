from langchain_core.messages import SystemMessage, ToolMessage, AIMessage, HumanMessage
from .tools_registry import AVAILABLE_TOOLS, tool_registry, get_router_llm, get_reasoner_llm
from .harvey_prompt import STATIC_SYSTEM_PROMPT, DYNAMIC_PROMPT
from .summarizer import summarize
from django.utils import timezone
from django.contrib.auth import get_user_model
import json, time
import datetime
import logging
import pytz

logger = logging.getLogger("harvey")

User = get_user_model()

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

    content = last_msg.content.lower()
    draft = get_state_value(state, "draft_email")
    if content.strip() == "send" and draft:
        return {"intent": "tool", "target_tool": "send_email_tool"}

    if "draft" in content and "send" not in content:
        return {"intent": "chat", "target_tool": None}

    llm = get_router_llm().bind(temperature=0)
    
    # Names-only for token efficiency
    tools_desc = ", ".join(t.name for t in AVAILABLE_TOOLS)
    
    # Pass last 4 messages to router for better intent classification
    last_msgs = messages[-4:]
    last_msgs_text = "\n".join([f"{m.type}: {m.content}" for m in last_msgs])
    
    parser = JsonOutputParser(pydantic_object=RouterOutput)
    
    router_prompt = f"""
    Classify intent correctly.
    {parser.get_format_instructions()}

    TOOLS: {tools_desc}

    Rules:
    - Use "tool" for actions (schedule, send) OR info-seeking (who is X, what is policy Y).
    - Use "chat" ONLY for greetings, thanks, or purely conversational non-technical talk.
    - If the user asks to "send" an email or "email" someone -> ALWAYS use send_email_tool.
    - If the user asks to "draft" AND "send", use send_email_tool (intent is action).
    - ONLY use "chat" if the user ONLY wants to draft without sending.
    - If user asks about a person, candidate, or staff -> search_knowledge_base.
    - If user asks about a policy or rule -> search_policies.
    - "interview" → schedule_interview

    Response MUST be raw JSON. No markdown code blocks. No preamble.

    History:
    {last_msgs_text}
    """
    
    try:
        logger.info("Router (8B) analyzing...")
        start = time.time()
        
        # We use a simple chain
        chain = llm | parser
        result = chain.invoke(router_prompt)
        
        # Defensive normalization: Sometimes LLM puts tool name in intent
        intent = result.get("intent", "chat").lower()
        tool_name = result.get("tool_name", "None") or "None"
        
        if intent not in ["tool", "chat"]:
            # If intent is a tool name, swap it
            if intent in tool_registry:
                tool_name = intent
                intent = "tool"
            else:
                intent = "chat"

        if tool_name == "None":
             tool_name = None

        duration = int((time.time() - start) * 1000)
        logger.info(f"Router Decision: {{'intent': {intent}, 'tool': {tool_name}}} ({duration}ms)")
        
        append_trace(state, {
            "node": "ROUTER",
            "decision": {"intent": intent, "tool": tool_name},
            "duration": duration
        })

        # Reset state on intent change or tool selection
        updates = {"intent": intent, "target_tool": tool_name}
        if intent == "chat":
            updates["pending_tool"] = None
            updates["requires_approval"] = False
            
        return updates

    except Exception as e:
        logger.error(f"Router failed: {e}")
        # Fallback to safe \"chat\"
        return {"intent": "chat", "target_tool": None}

def harvey_node(state):
    messages = get_state_value(state, "messages", [])
    intent = get_state_value(state, "intent", "chat")

    # 🔁 If last message was tool output, bypass LLM
    if messages and isinstance(messages[-1], ToolMessage):
        logger.info("[INFO] Harvey Node: Bypassing LLM (Returning Tool Output Directly)")
        return {}

    # --- MODEL SELECTION ---
    if intent == "chat":
        llm = get_router_llm()
        logger.info("[INFO] Harvey Node: Using 8B Model (Chat Mode)")
    else:
        llm = get_reasoner_llm()
        logger.info("[INFO] Harvey Node: Using 70B Model (Tool Mode)")

    context = get_state_value(state, "context", {})

    current_goal = context.get("current_goal", "None")
    last_active_topic = context.get("last_active_topic", "None")
    extracted_info = json.dumps(context.get("extracted_info", {}), indent=2)

    tools_str = (
        "No tools available in Chat Mode."
        if intent == "chat"
        else "\n".join(f"- {t.name}: {t.description}" for t in AVAILABLE_TOOLS)
    )

    # --- TIME CONTEXT ---
    ist = pytz.timezone("Asia/Kolkata")
    now_ist = timezone.now().astimezone(ist)
    current_date_text = now_ist.strftime("%A, %B %d, %Y, %I:%M %p")
    user_timezone = "IST (UTC+05:30)"

    target_tool_hint = ""
    target_tool = get_state_value(state, "target_tool")
    if intent == "tool" and target_tool:
        target_tool_hint = (
            f"\nROUTER HINT: The user specifically wants to use '{target_tool}'."
        )

    sys = (
        STATIC_SYSTEM_PROMPT
        + DYNAMIC_PROMPT.format(
            current_goal=current_goal,
            current_date=f"{current_date_text} {user_timezone}",
            last_active_topic=last_active_topic,
            extracted_info=extracted_info,
            tools=tools_str,
        )
        + target_tool_hint
    )

    if intent == "chat":
        sys += (
            "\n\nMODE: CHAT. No tools available. "
            "If user asks to draft, generate draft only."
        )

    history_size = 6 if intent == "tool" else 4
    history = messages[-history_size:]
    msgs = [SystemMessage(content=sys)] + history

    start = time.time()

    try:
        if intent == "tool":
            result = llm.bind_tools(AVAILABLE_TOOLS).invoke(msgs)
        else:
            result = llm.invoke(msgs)

        append_trace(state, {
            "node": "HARVEY",
            "duration_ms": int((time.time() - start) * 1000),
            "tool_call": bool(result.tool_calls),
        })

        # Build user text once
        user_text = " ".join(
            m.content.lower()
            for m in messages
            if isinstance(m, HumanMessage)
        )

        # --- TOOL HANDLING ---
        if result.tool_calls:
            tool_call = result.tool_calls[0]
            tool_name = tool_call["name"]
            draft_requested = "draft" in user_text

            # ✉️ EMAIL DRAFT — SINGLE SOURCE OF TRUTH
            if tool_name == "send_email_tool" and draft_requested:
                set_state_value(state, "draft_email", {
                    "recipient": tool_call["args"].get("recipient_email"),
                    "subject": tool_call["args"].get("subject"),
                    "body": result.content.strip(),
                })

            logger.info(f"Harvey decided to use tool: {tool_name}")

            return {
                "messages": [result],
                "pending_tool": tool_call,
                "requires_approval": False,
            }

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
    if not call:
        return {}
    draft = get_state_value(state, "draft_email")

    # 🔒 HARD OVERRIDE: draft is the single source of truth
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
        logger.info(f"Executing tool: {call['name']} with args: {args}")

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

        return {
            "messages": [ToolMessage(tool_call_id=call["id"], content=message)],
            "pending_tool": None,
            "requires_approval": False
        }

    except Exception as e:
        logger.error(f"Tool execution failed: {e}")
        append_trace(state, {
            "node": "TOOL",
            "tool": call["name"],
            "error": str(e)
        })
        set_state_value(state, "pending_tool", None)
        return {
            "messages": [AIMessage(content=f"Tool failed: {e}")],
            "pending_tool": None,
            "requires_approval": False
        }


def summary_node(state):
    messages = get_state_value(state, "messages", [])
    
    # Skip summary after tool execution
    if messages and isinstance(messages[-1], ToolMessage):
        return {}
        
    last = messages[-1] if messages else None
    # Only summarize when history gets long and user has replied
    if isinstance(last, HumanMessage) and len(messages) >= 8:
        new_context = summarize(messages)
        logger.debug(f"Updated Context: {new_context}")
    else:
        new_context = None

    updates = {"pending_tool": None, "requires_approval": False}
    if new_context:
        updates["context"] = new_context
        # Prune history to last 4 messages after summarization
        updates["messages"] = messages[-4:]
        
    return updates