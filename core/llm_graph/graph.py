# from langgraph.graph import StateGraph
# from langgraph.checkpoint.redis import RedisSaver
# from core.redis_utils import r
# from .state import HarveyState
# from .nodes import harvey_node, execute_node, should_execute, summary_node

# # Redis-based persistent checkpointing
# checkpointer = RedisSaver(
#     redis_url="redis://host.docker.internal:6379/0",
#     ttl={"checkpoint": 60 * 60 * 4}
# )
# workflow = StateGraph(HarveyState)

# workflow.add_node("HARVEY", harvey_node)
# workflow.add_node("TOOL", execute_node)
# workflow.add_node("SUM", summary_node)

# workflow.set_entry_point("HARVEY")

# workflow.add_conditional_edges(
#     "HARVEY",
#     should_execute,
#     {True: "TOOL", False: "SUM"}
# )

# workflow.add_edge("TOOL", "SUM")

# graph = workflow.compile(checkpointer=checkpointer)


import sqlite3
from langgraph.graph import StateGraph
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

from .state import HarveyState
from .nodes import harvey_node, execute_node, should_execute, summary_node

# Ensure DB creates tables automatically with pickle fallback enabled
serde = JsonPlusSerializer(pickle_fallback=True)

conn = sqlite3.connect("checkpoints.db", check_same_thread=False)

checkpointer = SqliteSaver(
    conn,
    serde=serde
)
workflow = StateGraph(HarveyState)

workflow.add_node("HARVEY", harvey_node)
workflow.add_node("TOOL", execute_node)
workflow.add_node("SUM", summary_node)

workflow.set_entry_point("HARVEY")

workflow.add_conditional_edges(
    "HARVEY",
    should_execute,
    {True: "TOOL", False: "SUM"}
)

workflow.add_edge("TOOL", "SUM")

graph = workflow.compile(checkpointer=checkpointer)