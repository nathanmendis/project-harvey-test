
import sqlite3
from langgraph.graph import StateGraph
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

from .state import HarveyState
from .nodes import harvey_node, execute_node, should_execute, summary_node, router_node

# Ensure DB creates tables automatically with pickle fallback enabled
serde = JsonPlusSerializer(pickle_fallback=True)

conn = sqlite3.connect("checkpoints.db", check_same_thread=False)

checkpointer = SqliteSaver(
    conn,
    serde=serde
)

workflow = StateGraph(HarveyState)

workflow.add_node("ROUTER", router_node)
workflow.add_node("HARVEY", harvey_node)
workflow.add_node("TOOL", execute_node)
workflow.add_node("SUM", summary_node)

workflow.set_entry_point("ROUTER")
workflow.add_edge("ROUTER", "HARVEY")

# ... (rest of edges) ...

workflow.add_conditional_edges(
    "HARVEY",
    should_execute,
    {True: "TOOL", False: "SUM"}
)

workflow.add_edge("TOOL", "HARVEY")

graph = workflow.compile(checkpointer=checkpointer)