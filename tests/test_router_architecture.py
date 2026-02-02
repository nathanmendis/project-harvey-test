import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# 1. Add project root to sys.path so we can import 'core'
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 2. Setup Django (Required because 'core.llm_graph.nodes' imports User model at module level)
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project_harvey.settings")
django.setup()

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from core.llm_graph.nodes import router_node, harvey_node, SENSITIVE_TOOLS
from core.llm_graph.state import HarveyState

class TestRouterArchitecture(unittest.TestCase):

    @patch("core.llm_graph.nodes.get_router_llm")
    def test_router_node_chat_intent(self, mock_get_router):
        """Test that router_node correctly identifies CHAT intent."""
        # Setup Mock 8B Model
        mock_llm = MagicMock()
        mock_chain = MagicMock()
        
        # correctly mocking the chain logic: llm | parser -> chain.invoke()
        # In the actual code: chain = llm | parser. 
        # But we can just mock the chain behavior if we look at how it's constructed, 
        # or easier: mock the return value of invoke if we patch the right thing.
        # Actually, `router_node` does: `chain = llm | parser`. 
        # It's safer to mock the whole execution or just the output if we can.
        # Let's mock the chain.invoke return value.
        
        # Issue: `llm | parser` creates a RunnableSequence. 
        # A simpler way is to mock `chain.invoke` but keeping `llm | parser` working is hard.
        # Alternative: We can patch `JsonOutputParser` too? 
        # Or simpler: The code does `chain.invoke(router_prompt)`.
        
        # Let's try to mock the result of the chain directly if we can intercept it,
        # but interception inside the function is hard.
        
        # Approach: Mock the LLM to return a raw string (if parser works) 
        # OR patch the `chain.invoke` if we could.
        # Given the code struct: `chain = llm | parser`.
        # If we make `mock_llm` implement `__or__` it might work.
        
        # EASIEST APPROACH: Patch `Chain.invoke`? No.
        # Let's assume we can mock the behavior:
        
        mock_runnable = MagicMock()
        mock_runnable.invoke.return_value = {"intent": "chat", "tool_name": None}
        
        # When llm | parser happens, return mock_runnable
        mock_llm.__or__.return_value = mock_runnable
        mock_get_router.return_value = mock_llm

        # Input State
        state = {"messages": [HumanMessage(content="Hello there!")]}
        
        # Run Node
        result = router_node(state)
        
        # Assertions
        self.assertEqual(result["intent"], "chat")
        self.assertIsNone(result["target_tool"])
        print("\n✅ Router correctly identified CHAT intent.")

    @patch("core.llm_graph.nodes.get_router_llm")
    def test_router_node_tool_intent(self, mock_get_router):
        """Test that router_node correctly identifies TOOL intent."""
        
        # Setup Mock to return a tool decision
        mock_runnable = MagicMock()
        mock_runnable.invoke.return_value = {
            "intent": "tool", 
            "tool_name": "create_calendar_event_tool"
        }
        
        mock_llm = MagicMock()
        mock_llm.__or__.return_value = mock_runnable
        mock_get_router.return_value = mock_llm

        state = {"messages": [HumanMessage(content="Book a meeting")]}
        
        result = router_node(state)
        
        self.assertEqual(result["intent"], "tool")
        self.assertEqual(result["target_tool"], "create_calendar_event_tool")
        print("\n✅ Router correctly identified TOOL intent.")

    @patch("core.llm_graph.nodes.get_reasoner_llm")
    def test_harvey_node_respects_chat_intent(self, mock_get_reasoner):
        """Test that 70B model is invoked WITHOUT tools when intent is chat."""
        mock_llm = MagicMock()
        mock_get_reasoner.return_value = mock_llm
        
        # Setup state
        state = {
            "messages": [HumanMessage(content="Hello")],
            "intent": "chat",
            "context": {},
            "requires_approval": False
        }
        
        # Run node
        harvey_node(state)
        
        # Assert calls
        # Should have called invoke(), but NOT bind_tools().invoke()
        # We can check if bind_tools was called.
        mock_llm.bind_tools.assert_not_called()
        mock_llm.invoke.assert_called_once()
        print("\n✅ Harvey (70B) respected CHAT intent (No tools bound).")

    @patch("core.llm_graph.nodes.get_reasoner_llm")
    def test_harvey_node_respects_tool_intent(self, mock_get_reasoner):
        """Test that 70B model IS invoked WITH tools when intent is tool."""
        mock_llm = MagicMock()
        # bind_tools returns a runnable (usually the LLM itself with tools), 
        # so we need to mock the return of bind_tools to allow invoke()
        mock_bound_llm = MagicMock()
        mock_llm.bind_tools.return_value = mock_bound_llm
        
        # Mock the result of invoke to be a simple message so it doesn't crash
        mock_bound_llm.invoke.return_value = AIMessage(content="Sure, I can help.")
        
        mock_get_reasoner.return_value = mock_llm
        
        state = {
            "messages": [HumanMessage(content="Do task")],
            "intent": "tool",
            "target_tool": "some_tool",
            "context": {},
            "requires_approval": False
        }
        
        harvey_node(state)
        
        mock_llm.bind_tools.assert_called_once()
        mock_bound_llm.invoke.assert_called_once()
        print("\n✅ Harvey (70B) respected TOOL intent (Tools bound).")

    @patch("core.llm_graph.nodes.get_reasoner_llm")
    def test_hil_interception(self, mock_get_reasoner):
        """Test that Harvey node intercepts sensitive tools."""
        
        mock_llm = MagicMock()
        mock_bound_llm = MagicMock()
        mock_llm.bind_tools.return_value = mock_bound_llm
        mock_get_reasoner.return_value = mock_llm

        # Create a mock result that LOOKS like a Sensitive Tool Call
        sensitive_tool = "create_calendar_event_tool" # Ensure this matches SENSITIVE_TOOLS
        mock_tool_call = {
            "name": sensitive_tool,
            "args": {"title": "Meeting"},
            "id": "call_123",
            "type": "tool_call"
        }
        
        # The LLM output
        mock_result_msg = AIMessage(content="", tool_calls=[mock_tool_call])
        mock_bound_llm.invoke.return_value = mock_result_msg
        
        state = {
            "messages": [HumanMessage(content="Book a meeting")],
            "intent": "tool",
            "context": {}
        }
        
        result = harvey_node(state)
        
        # Assertions
        self.assertTrue(result["requires_approval"], "Should require approval")
        self.assertEqual(result["pending_tool"], mock_tool_call)
        # Check that the returned message asks for confirmation
        self.assertIn("Do you want me to proceed?", result["messages"][0].content)
        print("\n✅ Harvey intercepted SENSITIVE tool correctly.")

if __name__ == "__main__":
    unittest.main()
