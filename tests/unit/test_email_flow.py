import json
from django.test import TestCase
from unittest.mock import MagicMock, patch
from langchain_core.messages import AIMessage, HumanMessage
from core.llm_graph.graph import graph
from core.models.organization import Organization, User

from core.models.recruitment import EmailLog

class EmailFlowTest(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="Test Org")
        self.user = User.objects.create_user(username="testuser", password="password", organization=self.org)

    @patch("core.llm_graph.nodes.get_llm")
    def test_email_tool_execution(self, mock_get_llm):
        # Setup mock LLM to return a tool call
        mock_llm = MagicMock()
        mock_get_llm.return_value = mock_llm
        
        # Mock the bind_tools().invoke() chain
        mock_bound_llm = MagicMock()
        mock_llm.bind_tools.return_value = mock_bound_llm
        
        # Define the tool call message
        tool_call_msg = AIMessage(
            content="",
            tool_calls=[{
                "name": "send_email_tool",
                "args": {
                    "recipient_email": "nathan@gmail.com",
                    "subject": "Test Meeting",
                    "body": "Please attend."
                },
                "id": "call_123"
            }]
        )
        
        final_msg = AIMessage(content="Email sent to nathan@gmail.com")
        mock_bound_llm.invoke.side_effect = [tool_call_msg, final_msg]
        
        # Prepare state input
        state_input = {
            "messages": [HumanMessage(content="Send an email to nathan@gmail.com")],
            "user_id": self.user.id,
            "context": {}
        }
        
        # Run the graph without mocking the tool registry
        # This ensures the REAL send_email_tool is called, which should log to DB
        
        result = graph.invoke(state_input, config={"configurable": {"thread_id": "test_thread"}})
        
        # Verify results
        # 1. Check if LLM was called
        mock_bound_llm.invoke.assert_called()
        
        # 2. Check if EmailLog was created
        self.assertEqual(EmailLog.objects.count(), 1)
        log = EmailLog.objects.first()
        self.assertEqual(log.recipient_email, "nathan@gmail.com")
        self.assertEqual(log.subject, "Test Meeting")
        self.assertEqual(log.body, "Please attend.")
        self.assertEqual(log.organization, self.org)
        
        # 3. Check if the final message indicates success
        last_message = result["messages"][-1]
        self.assertIn("Email sent to nathan@gmail.com", last_message.content)
