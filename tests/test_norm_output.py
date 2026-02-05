import json
from django.test import TestCase
from core.ai.rag.tools.search_tool import search_knowledge_base
from core.ai.rag.tools.policy_search_tool import search_policies

class TestNormalization(TestCase):
    def test_normalization(self):
        """Testing Knowledge Base and Policy Normalization."""
        kb_result = search_knowledge_base.invoke({"query": "steve"})
        kb_data = json.loads(kb_result)
        self.assertIn('ok', kb_data)

        policy_result = search_policies.invoke({"query": "leave policy"})
        policy_data = json.loads(policy_result)
        self.assertIn('ok', policy_data)
