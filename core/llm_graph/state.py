

from langgraph.graph import MessagesState
from typing import Optional, Dict, List, Any
from pydantic import Field

class HarveyState(MessagesState):
    summary: Optional[str] = None
    context: Dict[str, Any] = Field(default_factory=dict)  # Structured context
    pending_tool: Optional[Dict] = None
    trace: List[Dict[str, Any]] = Field(default_factory=list)
    user_id: Optional[int] = None
    requires_approval: bool = False
    
    # Routing
    intent: Optional[str] = None  # "chat" or "tool"
    target_tool: Optional[str] = None # Name of tool if intent is tool