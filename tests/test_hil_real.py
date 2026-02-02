
import os
import django
import sys
import time
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

# Setup Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project_harvey.settings')
django.setup()

from core.llm_graph.nodes import harvey_node, should_execute, execute_node, summary_node, get_llm
from core.llm_graph.state import HarveyState

def test_hil_real():
    print("🚀 Starting HIL Confirmation Logic Test (REAL LLM)")
    
    # 1. Setup Initial State
    state = HarveyState(
        messages=[HumanMessage(content="Schedule a meeting for tomorrow at 10am called 'Strategy Sync' with nathan@example.com")],
        context={},
        trace=[],
        pending_tool=None,
        requires_approval=False
    )

    print("\n--- STEP 1: Harvey Node (User asks for meeting) ---")
    # This calls the REAL LLM
    result = harvey_node(state)
    
    # Verify Interception
    print(f"Result Keys: {result.keys()}")
    if result.get("requires_approval"):
        print("✅ Interception Successful: `requires_approval` is True")
        print(f"Draft Message: {result['messages'][0].content}")
    else:
        print("❌ Interception FAILED: `requires_approval` missing or False")
        tool_call = result.get("pending_tool")
        if tool_call:
             print(f"Tool was called directly: {tool_call['name']}")
        else:
             print("No tool call generated.")
        return

    # Update state manually (simulating graph)
    state['messages'].extend(result['messages'])
    state['pending_tool'] = result['pending_tool']
    state['requires_approval'] = result['requires_approval']

    # 3. Check Condition (Should we execute?)
    print("\n--- STEP 2: Should Execute Check (Before Confirmation) ---")
    should_run = should_execute(state)
    print(f"Should Execute? {should_run}")
    if not should_run:
        print("✅ Correct: Execution halted pending approval.")
    else:
        print("❌ Incorrect: Execution proceeded despite approval needed.")
        return

    # 5. User Confirms
    print("\n--- STEP 3: User Says 'Yes' ---")
    state['messages'].append(HumanMessage(content="Yes, go ahead"))
    
    # Run Harvey Node again (it handles the confirmation check)
    result = harvey_node(state)
    
    # print(f"Result: {result}")
    if result.get("requires_approval") is False:
            print("✅ Confirmation Accepted: `requires_approval` set to False")
    else:
            print("❌ Confirmation Failed: Logic did not accept 'Yes'")
            print(f"Response: {result.get('messages')}")
            return
            
    # Update State
    state['requires_approval'] = result['requires_approval']
    
    # NOTE: In the real nodes.py, we return result["pending_tool"] = pending_tool if confirmed.
    if result.get("pending_tool"):
        state['pending_tool'] = result['pending_tool']

    # 6. Check Condition (Should we execute now?)
    print("\n--- STEP 4: Should Execute Check (After Confirmation) ---")
    should_run = should_execute(state)
    print(f"Should Execute? {should_run}")
    if should_run:
        print("✅ Correct: Execution allowed.")
        print(f"Pending tool to run: {state['pending_tool']['name']}")
    else:
        print("❌ Incorrect: Execution halted.")
        return
        
    print("\n🎉 TEST COMPLETE: Real LLM Flow Verified.")

if __name__ == "__main__":
    test_hil_real()
