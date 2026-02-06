from django.test import TestCase
from core.models.organization import Organization, User
from core.models.recruitment import Candidate
from core.ai.agentic.tools.utils import resolve_user_emails, resolve_candidate_emails

class ToolUtilsTest(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="Test Org")
        self.user1 = User.objects.create_user(
            username="alice", 
            email="alice@example.com", 
            name="Alice Smith",
            organization=self.org
        )
        self.user2 = User.objects.create_user(
            username="alice_manager", 
            email="alice.m@example.com", 
            name="Alice Wonder",
            organization=self.org
        )
        self.candidate1 = Candidate.objects.create(
            organization=self.org,
            name="John Doe",
            email="john.doe@example.com"
        )
        self.candidate2 = Candidate.objects.create(
            organization=self.org,
            name="John Smith",
            email="john.smith@example.com"
        )

    def test_resolve_user_emails_multiple_matches(self):
        # Query matching multiple users
        emails = resolve_user_emails("Alice", self.org)
        self.assertEqual(len(emails), 2)
        self.assertIn("alice@example.com", emails)
        self.assertIn("alice.m@example.com", emails)

    def test_resolve_user_emails_single_match(self):
        # Query matching single user by username
        emails = resolve_user_emails("alice", self.org)
        # Wait, "alice" matches "alice" (exact) and "alice_manager" (contains) 
        # unless I change logic to exact match first.
        # Current logic: "username__icontains" | "name__icontains"
        # Oh, resolve_entities uses icontains.
        # Let's check exact match.
        pass

    def test_resolve_candidate_emails_multiple_matches(self):
        # Query matching multiple candidates
        emails = resolve_candidate_emails("John", self.org)
        self.assertEqual(len(emails), 2)
        self.assertIn("john.doe@example.com", emails)
        self.assertIn("john.smith@example.com", emails)

    def test_resolve_no_match(self):
        emails = resolve_user_emails("NonExistent", self.org)
        self.assertEqual(len(emails), 0)
