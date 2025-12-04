import os
import django
import sys
from langchain_core.messages import HumanMessage, AIMessage

# Setup Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project_harvey.settings')
django.setup()

from core.llm_graph.summarizer import summarize
from core.llm_graph.nodes import harvey_node, summary_node
from core.llm_graph.state import HarveyState

def test_context_switching():
    print("--- Testing Context Switching ---")
    messages = [
        HumanMessage(content="I need to schedule an interview with Alice for the Senior Dev role."),
        AIMessage(content="Sure, I can help with that. When would you like to schedule it?"),
        HumanMessage(content="Actually, wait. What is the policy for paternity leave?"),
    ]
    
    context = summarize(messages)
    print("Context after switch:", context)
    
    # Simulate switching back
    messages.append(AIMessage(content="Paternity leave is 2 weeks paid."))
    messages.append(HumanMessage(content="Okay, thanks. Back to Alice, let's do next Tuesday at 2pm."))
    
    context = summarize(messages)
    print("Context after switch back:", context)

def test_hallucination_prompt():
    print("\n--- Testing Prompt Formatting ---")
    state = HarveyState(
        messages=[],
        context={
            "current_goal": "Schedule interview",
            "last_active_topic": "recruiting",
            "extracted_info": {"candidate": "Alice"}
        }
    )
    
    # We can't easily invoke the full node without mocking LLM, 
    # but we can check if the prompt construction would work if we could inspect it.
    print("State context:", state["context"])

def test_stale_tool_clearance():
    print("\n--- Testing Stale Tool Clearance ---")
    # Simulate state where a tool was pending but user changed topic (so we reached summary_node)
    state = HarveyState(
        messages=[HumanMessage(content="Ignore that, let's do something else")],
        pending_tool={"name": "send_email", "args": {}},
        context={}
    )
    
    # Run summary node
    updates = summary_node(state)
    print("Summary node updates:", updates)
    
    if updates.get("pending_tool") is None:
        print("SUCCESS: pending_tool was cleared.")
    else:
        print("FAILURE: pending_tool was NOT cleared.")

if __name__ == "__main__":
    test_context_switching()
    test_hallucination_prompt()
    test_stale_tool_clearance()
