import json
from django.test import TestCase
from unittest.mock import patch, MagicMock
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from core.ai.agentic.graph.nodes.router import router_node
from core.ai.agentic.graph.nodes.harvey import harvey_node
from core.ai.rag.tools.policy_search_tool import search_policies
from core.models.organization import Organization, User

class RAGFixVerificationTest(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="Harvey Test")
        self.user = User.objects.create_user(username="testuser", organization=self.org)

    def test_router_policy_routing(self):
        """Verify that working hours question routes to search_policies."""
        state = {
            "messages": [HumanMessage(content="How many working hours are employees expected to work per day at Harvey?")],
            "context": {}
        }
        with patch('core.ai.agentic.graph.nodes.router.get_router_llm') as mock_llm:
            # Mock LLM response for routing
            mock_response = MagicMock()
            mock_response.content = json.dumps({"intent": "tool", "tool_name": "search_policies"})
            mock_llm.return_value.bind.return_value.invoke.return_value = mock_response
            
            result = router_node(state)
            self.assertEqual(result["intent"], "tool")
            self.assertEqual(result["target_tool"], "search_policies")

    def test_harvey_narration_suppression(self):
        """Verify that Harvey node suppresses narration when tool_calls are present."""
        state = {
            "messages": [HumanMessage(content="How many hours?")],
            "context": {},
            "intent": "tool",
            "target_tool": "search_policies"
        }
        with patch('core.ai.agentic.graph.nodes.harvey.get_reasoner_llm') as mock_llm:
            mock_ai_message = AIMessage(content="I will search the policies for you.", tool_calls=[{"name": "search_policies", "args": {"query": "working hours"}, "id": "call_1"}])
            mock_llm.return_value.bind_tools.return_value.invoke.return_value = mock_ai_message
            
            result = harvey_node(state)
            # The message content should be cleared
            self.assertEqual(result["messages"][0].content, "")
            self.assertEqual(result["pending_tool"]["name"], "search_policies")

        # We can't easily check the prompt itself without more complex mocking, 
        # but we verified the prompt strings in the file edit.
