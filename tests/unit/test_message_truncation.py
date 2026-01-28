from django.test import TestCase
from unittest.mock import patch, MagicMock
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from core.llm_graph.nodes import harvey_node

class MessageTruncationTest(TestCase):
    
    @patch("core.llm_graph.nodes.get_llm")
    def test_message_truncation(self, mock_get_llm):
        # Setup Mock LLM
        mock_llm_instance = MagicMock()
        mock_get_llm.return_value = mock_llm_instance
        
        # Make the bind_tools call return the mock instance itself so invoke works
        mock_llm_instance.bind_tools.return_value = mock_llm_instance
        
        # Create a state with 20 messages (older to newer)
        messages = [HumanMessage(content=f"Available message {i}") for i in range(20)]
        state = {
            "messages": messages,
            "context": {},
            "trace": []
        }
        
        # Execute Node
        harvey_node(state)
        
        # Verify arguments passed to invoke
        # We expect: [SystemMessage, msg[10], msg[11], ... msg[19]] -> total 11 items
        args, _ = mock_llm_instance.invoke.call_args
        passed_messages = args[0]
        
        print(f"\nTotal messages passed to LLM: {len(passed_messages)}")
        
        # Assertions
        self.assertEqual(len(passed_messages), 11, "Should contain 1 SystemMessage + 10 ChatMessages")
        self.assertIsInstance(passed_messages[0], SystemMessage, "First message must be SystemMessage")
        self.assertEqual(passed_messages[1].content, "Available message 10", "Should start from the 11th message (index 10)")
        self.assertEqual(passed_messages[-1].content, "Available message 19", "Should end with the last message")
