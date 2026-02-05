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
from core.llm_graph.nodes import router_node, harvey_node
from core.llm_graph.state import HarveyState

class TestRouterArchitecture(unittest.TestCase):

    @patch("core.llm_graph.nodes.get_router_llm")
    def test_router_node_meeting_vs_interview(self, mock_get_router):
        """Verify that 'meeting' uses calendar and 'interview' uses interview tool."""
        mock_llm = MagicMock()
        mock_bound = MagicMock()
        mock_runnable = MagicMock()
        mock_get_router.return_value = mock_llm
        mock_llm.bind.return_value = mock_bound
        mock_bound.__or__.return_value = mock_runnable

        # 1. Test "meeting"
        mock_runnable.invoke.return_value = {
            "intent": "tool",
            "tool_name": "create_calendar_event_tool"
        }
        state_meeting = {"messages": [HumanMessage(content="Schedule a meeting")]}
        res_meeting = router_node(state_meeting)
        self.assertEqual(res_meeting["target_tool"], "create_calendar_event_tool")

        # 2. Test "interview"
        mock_runnable.invoke.return_value = {
            "intent": "tool",
            "tool_name": "schedule_interview"
        }
        state_interview = {"messages": [HumanMessage(content="Schedule an interview")]}
        res_interview = router_node(state_interview)
        self.assertEqual(res_interview["target_tool"], "schedule_interview")
        self.assertEqual(res_interview["intent"], "tool")

    @patch("core.llm_graph.nodes.get_router_llm")
    def test_harvey_node_uses_8b_for_chat(self, mock_get_router):
        """Test that 8B model is invoked for chat."""
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = AIMessage(content="Hi")
        mock_get_router.return_value = mock_llm
        
        state = {
            "messages": [HumanMessage(content="Hello")],
            "intent": "chat",
            "context": {},
            "requires_approval": False
        }
        
        harvey_node(state)
        mock_llm.invoke.assert_called_once()
        print("\n✅ Harvey (8B) used for CHAT.")

    @patch("core.llm_graph.nodes.get_reasoner_llm")
    def test_harvey_node_uses_70b_for_tools(self, mock_get_reasoner):
        """Test that 70B model is used for tools and binds tools."""
        mock_llm = MagicMock()
        mock_bound_llm = MagicMock()
        mock_llm.bind_tools.return_value = mock_bound_llm
        mock_bound_llm.invoke.return_value = AIMessage(content="Sure")
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
        print("\n✅ Harvey (8B) used for TOOL.")

    @patch("core.llm_graph.nodes.get_reasoner_llm")
    def test_no_hil_interception(self, mock_get_reasoner):
        """Test that Harvey node NO LONGER intercepts sensitive tools (direct execution)."""
        mock_llm = MagicMock()
        mock_bound_llm = MagicMock()
        mock_llm.bind_tools.return_value = mock_bound_llm
        mock_get_reasoner.return_value = mock_llm

        sensitive_tool = "create_calendar_event_tool"
        mock_tool_call = {
            "name": sensitive_tool,
            "args": {"title": "Meeting"},
            "id": "call_123",
            "type": "tool_call"
        }
        
        mock_result_msg = AIMessage(content="", tool_calls=[mock_tool_call])
        mock_bound_llm.invoke.return_value = mock_result_msg
        
        state = {
            "messages": [HumanMessage(content="Book a meeting")],
            "intent": "tool",
            "context": {}
        }
        
        result = harvey_node(state)
        
        # Assertions: Should NOT require approval, should have tool call ready
        self.assertFalse(result.get("requires_approval", False), "Should NOT require approval")
        self.assertEqual(result["pending_tool"], mock_tool_call)
        print("\n✅ Harvey did NOT intercept sensitive tool (Direct execution enabled).")

if __name__ == "__main__":
    unittest.main()
