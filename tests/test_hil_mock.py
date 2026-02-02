
import os
import django
import sys
from unittest.mock import MagicMock, patch

# Setup Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project_harvey.settings')
django.setup()

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from core.llm_graph.nodes import harvey_node, should_execute, execute_node, summary_node
from core.llm_graph.state import HarveyState

def test_hil_flow():
    print("🚀 Starting HIL Confirmation Logic Test (Mocked LLM)")
    
    # 1. Setup Initial State
    state = HarveyState(
        messages=[HumanMessage(content="Schedule a meeting for tomorrow")],
        context={},
        trace=[],
        pending_tool=None,
        requires_approval=False
    )

    # 2. Mocking the LLM to return a "Create Calendar Event" tool call
    mock_tool_call = {
        "name": "create_calendar_event_tool",
        "args": {"title": "Test Meeting", "start_time": "2024-01-01T10:00:00", "end_time": "2024-01-01T11:00:00", "attendees": "test@example.com"},
        "id": "call_mock_123"
    }
    
    mock_response = AIMessage(content="", tool_calls=[mock_tool_call])
    
    print("\n--- STEP 1: Harvey Node (User asks for meeting) ---")
    with patch('core.llm_graph.nodes.get_llm') as mock_get_llm:
        # Setup mock chain: llm.bind_tools(...).invoke(...) -> mock_response
        mock_llm = MagicMock()
        mock_bound = MagicMock()
        mock_bound.invoke.return_value = mock_response
        mock_llm.bind_tools.return_value = mock_bound
        mock_get_llm.return_value = mock_llm

        # Run Harvey Node
        result = harvey_node(state)
        
        # Verify Interception
        print(f"Result Keys: {result.keys()}")
        if result.get("requires_approval"):
            print("✅ Interception Successful: `requires_approval` is True")
            print(f"Draft Message: {result['messages'][0].content}")
        else:
            print("❌ Interception FAILED: `requires_approval` missing or False")
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

    # 4. Summary Node (Turn End)
    print("\n--- STEP 3: Summary Node (Preserve Pending Tool) ---")
    
    # Mocking summarize to avoid actual API call there too
    with patch('core.llm_graph.nodes.summarize') as mock_sum:
        mock_sum.return_value = {} # No context update
        updates = summary_node(state)
        print(f"Summary Updates: {updates}")
        
        if updates.get("pending_tool") is None:
             print("❌ FAIL: Summary node cleared `pending_tool`!")
        else:
             print("✅ Success: Summary node preserved `pending_tool`.")

    # 5. User Confirms
    print("\n--- STEP 4: User Says 'Yes' ---")
    state['messages'].append(HumanMessage(content="Yes, go ahead"))
    
    # Run Harvey Node again (it handles the confirmation check)
    with patch('core.llm_graph.nodes.get_llm') as mock_get_llm:
        # We don't even need the LLM here, the logic should short-circuit
        result = harvey_node(state)
        
        print(f"Result: {result}")
        if result.get("requires_approval") is False:
             print("✅ Confirmation Accepted: `requires_approval` set to False")
        else:
             print("❌ Confirmation Failed: Logic did not accept 'Yes'")
             return
             
        # Update State
        state['requires_approval'] = result['requires_approval']
        # Note: pending_tool is returned in result to keep it alive
        if result.get("pending_tool"):
            state['pending_tool'] = result['pending_tool']

    # 6. Check Condition (Should we execute now?)
    print("\n--- STEP 5: Should Execute Check (After Confirmation) ---")
    should_run = should_execute(state)
    print(f"Should Execute? {should_run}")
    if should_run:
        print("✅ Correct: Execution allowed.")
    else:
        print("❌ Incorrect: Execution halted.")
        return
        
    print("\n🎉 TEST COMPLETE: Logic Verified without LLM API.")

if __name__ == "__main__":
    test_hil_flow()
