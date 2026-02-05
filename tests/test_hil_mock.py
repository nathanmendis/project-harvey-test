from django.test import TestCase
from unittest.mock import MagicMock, patch
from langchain_core.messages import HumanMessage, AIMessage
from core.ai.agentic.graph.nodes import harvey_node, should_execute, summary_node
from core.ai.agentic.graph.state import HarveyState

class TestHILFlow(TestCase):

    def test_hil_flow(self):
        """Starting HIL Confirmation Logic Test (Mocked LLM)"""
        
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
        
        # --- STEP 1: Harvey Node (User asks for meeting) ---
        with patch('core.ai.agentic.graph.nodes.get_reasoner_llm') as mock_get_llm:
            mock_llm = MagicMock()
            mock_bound = MagicMock()
            mock_bound.invoke.return_value = mock_response
            mock_llm.bind_tools.return_value = mock_bound
            mock_get_llm.return_value = mock_llm

            # Mock and set intent to tool as router would
            state['intent'] = 'tool'
            result = harvey_node(state)
            
            # Verify Interception (Note: In v3.0, we no longer intercept, so requires_approval should be False)
            self.assertFalse(result.get("requires_approval", False))
            self.assertEqual(result['pending_tool'], mock_tool_call)

            # Update state manually (simulating graph)
            state['messages'].extend(result.get('messages', []))
            state['pending_tool'] = result['pending_tool']
            state['requires_approval'] = result.get('requires_approval', False)

        # --- STEP 2: Should Execute Check ---
        should_run = should_execute(state)
        self.assertTrue(should_run) # In v3.0, direct execution is enabled

        # --- STEP 3: Summary Node ---
        with patch('core.ai.agentic.graph.nodes.summarize') as mock_sum:
            mock_sum.return_value = {} 
            updates = summary_node(state)
            self.assertIsNotNone(updates.get("pending_tool"))
