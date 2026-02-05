from django.test import TestCase
from core.ai.agentic.graph.nodes import harvey_node
from core.models.organization import User, Organization
from langchain_core.messages import HumanMessage, AIMessage

class TestHallucination(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="Test Org")
        self.user = User.objects.create_user(username="test_hallucination", organization=self.org)

    def test_add_candidate_hallucination(self):
        """Testing Anti-Hallucination for Add Candidate."""
        state = {
            "messages": [
                HumanMessage(content="add candidate John Doe"),
                AIMessage(content="I'll need his email, phone, and skills."),
                HumanMessage(content="his email is jhon@gmial.com phone number is 283491458915 skills are python, django, MK")
            ],
            "user_id": self.user.id,
            "context": {},
            "trace": [],
            "intent": "tool"
        }
        
        result = harvey_node(state)
        self.assertIn("pending_tool", result)
        self.assertEqual(result["pending_tool"]["name"], "add_candidate")
