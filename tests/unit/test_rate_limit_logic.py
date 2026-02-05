from django.test import TestCase
from django.core.cache import cache
from core.models.organization import Organization, User
from core.ai.agentic.graph.chat_service import generate_llm_reply
from google.api_core.exceptions import ResourceExhausted
from unittest.mock import patch, MagicMock

class RateLimitTest(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="Test Org")
        self.user = User.objects.create_user(username="test_user", password="password", organization=self.org)
        cache.clear()

    @patch("core.ai.agentic.graph.chat_service.graph.invoke")
    def test_rate_limit_handling(self, mock_invoke):
        # 1. Simulate API Error (Rate Limit)
        mock_invoke.side_effect = ResourceExhausted("Quota exceeded")
        
        print("\n--- Testing Rate Limit Trigger ---")
        response = generate_llm_reply("Hello", self.user)
        
        # Verify immediate error response
        print(f"Response 1: {response.response}")
        self.assertIn("API Rate limit reached", response.response)
        
        # Verify cache block was set
        self.assertTrue(cache.get(f"chat_block_{self.user.id}"))
        
        # 2. Simulate User Trying Again (During Cool-down)
        print("\n--- Testing Cool-down Block ---")
        # Even if API is "fixed" now, block should persist
        mock_invoke.side_effect = None 
        
        response_2 = generate_llm_reply("Hello again", self.user)
        print(f"Response 2: {response_2.response}")
        
        self.assertIn("System is cooling down", response_2.response)
        
        print("--- Rate Limit Logic Verified ---")
