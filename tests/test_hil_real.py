import os
import unittest
from django.test import TestCase
from langchain_core.messages import HumanMessage
from core.ai.agentic.graph.nodes import harvey_node, should_execute
from core.ai.agentic.graph.state import HarveyState

class TestHILReal(TestCase):

    @unittest.skipIf(not os.environ.get("GROQ_API_KEY"), "GROQ_API_KEY not found")
    def test_hil_real_flow(self):
        """Starting HIL Confirmation Logic Test (REAL LLM)"""
        
        # 1. Setup Initial State
        state = HarveyState(
            messages=[HumanMessage(content="Schedule a meeting for tomorrow at 10am called 'Strategy Sync' with nathan@example.com")],
            context={},
            trace=[],
            pending_tool=None,
            requires_approval=False,
            intent="tool"
        )

        # --- STEP 1: Harvey Node (User asks for meeting) ---
        result = harvey_node(state)
        
        # In v3.0, we no longer intercept meetings by default unless explicitly asked to draft
        # So we check if a tool call was generated
        self.assertIn("pending_tool", result)
        tool_call = result["pending_tool"]
        self.assertEqual(tool_call["name"], "create_calendar_event_tool")

        # Update state manually (simulating graph)
        state['messages'].extend(result.get('messages', []))
        state['pending_tool'] = result['pending_tool']
        state['requires_approval'] = result.get('requires_approval', False)

        # --- STEP 2: Should Execute Check ---
        should_run = should_execute(state)
        self.assertTrue(should_run)
