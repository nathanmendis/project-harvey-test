import time
import logging
from langchain_core.messages import HumanMessage
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field
from ..tools_registry import AVAILABLE_TOOLS, tool_registry, get_router_llm
from .utils import get_state_value, append_trace, set_state_value

logger = logging.getLogger("harvey")

class RouterOutput(BaseModel):
    intent: str = Field(description="One of 'tool' or 'chat'")
    tool_name: str = Field(description="Name of the tool to use, or 'None' if chat", default="None")

def router_node(state):
    """
    Uses Llama-3-8B to classify user intent.
    Output: Updates 'intent' and 'target_tool' in state.
    """
    messages = get_state_value(state, "messages", [])
    if not messages:
        return {}

    last_msg = messages[-1]
    if not isinstance(last_msg, HumanMessage):
        return {"intent": "chat", "target_tool": None}

    content = last_msg.content.lower().strip()
    draft = get_state_value(state, "draft_email")
    if content == "send" and draft:
        return {"intent": "tool", "target_tool": "send_email_tool"}

    if "draft" in content and "send" not in content:
        return {"intent": "chat", "target_tool": None}

    llm = get_router_llm().bind(temperature=0)
    tools_desc = ", ".join(t.name for t in AVAILABLE_TOOLS)
    
    last_msgs = messages[-4:]
    last_msgs_text = "\n".join([f"{m.type}: {m.content}" for m in last_msgs])
    
    # TOKEN OPTIMIZED PROMPT
    router_prompt = f"""
    Determine user intent. Return ONLY a raw JSON object with these keys:
    - "intent": either "tool" (actions, searching info/policies) or "chat" (greetings, general talking, drafting without sending)
    - "tool_name": the exact name of the tool to use, or "None" if chat.
    
    AVAILABLE TOOLS: {tools_desc}
    
    Rules:
    - "send" email/draft -> send_email_tool.
    - Ask about person/staff -> search_knowledge_base.
    - Ask about policy, rule, working hours, attendance, or behavior -> search_policies.
    - User says "interview" -> schedule_interview.
    - User says "meeting", "calendar", "invite", "schedule" -> create_calendar_event_tool.
    - "chat" ONLY for greetings or drafting without sending.

    CRITICAL: Any question about Harvey's policies or how things work at Harvey MUST be "tool" with "search_policies". Do NOT guess or answer from general knowledge.

    History:
    {last_msgs_text}
    """
    
    try:
        logger.info("Router (8B) analyzing...")
        start = time.time()
        
        # LOG TOKENS: Break chain to get raw AIMessage
        response = llm.invoke(router_prompt)
        from .utils import log_token_usage
        log_token_usage(response, "Router (8B)")
        
        # Parse output manually to be robust and lightweight
        import re
        import json
        content = response.content.strip()
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].strip()

        try:
            result = json.loads(content)
        except Exception:
            # Fallback regex parser if output is slightly malformed JSON
            intent_match = re.search(r'"intent"\s*:\s*"([^"]+)"', content)
            tool_match = re.search(r'"tool_name"\s*:\s*"([^"]+)"', content)
            result = {
                "intent": intent_match.group(1) if intent_match else "chat",
                "tool_name": tool_match.group(1) if tool_match else "None"
            }

        intent = result.get("intent", "chat").lower()
        tool_name = result.get("tool_name", "None") or "None"
        
        if intent not in ["tool", "chat"]:
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


        updates = {"intent": intent, "target_tool": tool_name}
        if intent == "chat":
            updates["pending_tool"] = None
            updates["requires_approval"] = False
            
        return updates

    except Exception as e:
        logger.error(f"Router failed: {e}")
        return {"intent": "chat", "target_tool": None}
