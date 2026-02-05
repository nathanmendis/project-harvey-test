import json
from django.test import TestCase
from core.ai.rag.tools.policy_search_tool import search_policies

class TestLiteNLP(TestCase):
    def test_lite_nlp(self):
        """Testing Lite NLP Policy Normalization."""
        # This might require real LLM, but we check the structure
        policy_result = search_policies.invoke({"query": "leave policy"})
        policy_data = json.loads(policy_result)
        self.assertIn('ok', policy_data)
        self.assertIn('message', policy_data)
