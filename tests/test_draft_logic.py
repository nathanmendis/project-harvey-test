from django.test import TestCase
from core.ai.agentic.graph.chat_service import generate_llm_reply
from core.models.organization import Organization, User

class TestDraftLogic(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="Test Org")
        self.user = User.objects.create_user(username="testuser", organization=self.org)

    def test_draft_queries(self):
        """Verify Email Draft & Send Logic."""
        test_queries = [
            "draft an email to nathanmendis17@gmail.com saying thanks",
            "send email to nathanmendis17@gmail.com saying hi",
            "send email to nathanmendis17@gmail.com saying it is a test email but also draft the email"
        ]
        
        for query in test_queries:
            result = generate_llm_reply(query, self.user)
            self.assertIsNotNone(result)
            self.assertTrue(hasattr(result, 'response'))
            # We could do more specific assertions based on expected 'intent' in state, 
            # but generate_llm_reply returns a Response object.
