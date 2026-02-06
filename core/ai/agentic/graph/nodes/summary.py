import logging
from langchain_core.messages import HumanMessage, ToolMessage
from ..summarizer import summarize
from .utils import get_state_value

logger = logging.getLogger("harvey")

def summary_node(state):
    messages = get_state_value(state, "messages", [])
    if messages and isinstance(messages[-1], ToolMessage):
        return {}
        
    last = messages[-1] if messages else None
    if isinstance(last, HumanMessage) and len(messages) >= 8:
        new_context = summarize(messages)
        logger.debug(f"Updated Context: {new_context}")
    else:
        new_context = None

    updates = {"pending_tool": None, "requires_approval": False}
    if new_context:
        updates["context"] = new_context
        updates["messages"] = messages[-4:]
        
    return updates
