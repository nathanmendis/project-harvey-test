# from typing import Optional, Dict, List, Any
# from langgraph.graph import MessagesState
# from pydantic import Field

# class HarveyState(MessagesState):
#     summary: Optional[str] = None
#     pending_tool: Optional[Dict] = None
#     trace: List[Dict[str, Any]] = Field(default_factory=list)
#     user_id: Optional[int] = None  # store only ID to rehydrate safely
# from typing import Optional, Dict, List, Any
# from langgraph.graph import MessagesState
# from pydantic import Field

# class HarveyState(MessagesState):
#     summary: Optional[str] = None
#     pending_tool: Optional[Dict] = None
#     trace: List[Dict[str, Any]] = Field(default_factory=list)
#     user_id: Optional[int] = None  # store only ID to rehydrate safely


from langgraph.graph import MessagesState
from typing import Optional, Dict, List, Any
from pydantic import Field

class HarveyState(MessagesState):
    summary: Optional[str] = None
    context: Dict[str, Any] = Field(default_factory=dict)  # Structured context
    pending_tool: Optional[Dict] = None
    trace: List[Dict[str, Any]] = Field(default_factory=list)
    user_id: Optional[int] = None