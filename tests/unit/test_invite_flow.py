from django.test import TestCase, Client
from django.utils import timezone
from datetime import timedelta
from django.urls import reverse
from core.models.invite import Invite
from core.models.organization import User, Organization

class TestInviteFlow(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="Test Org")
        self.admin_user = User.objects.create_user(username="admin", password="password", organization=self.org, role="org_admin")
        self.client = Client()
        self.client.force_login(self.admin_user)

    def test_invite_model_creation(self):
        """Test that an invite can be created and is valid."""
        invite = Invite.objects.create(
            email="test@example.com",
            organization=self.org,
            role="employee",
            expires_at=timezone.now() + timedelta(days=7),
            created_by=self.admin_user
        )
        
        self.assertIsNotNone(invite.token)
        self.assertTrue(invite.is_valid())
        self.assertEqual(invite.role, "employee")
        self.assertEqual(invite.email, "test@example.com")

    def test_invite_expiration(self):
        """Test that expired invites are invalid."""
        invite = Invite.objects.create(
            email="expired@example.com",
            organization=self.org,
            expires_at=timezone.now() - timedelta(days=1)
        )
        self.assertFalse(invite.is_valid())

    def test_admin_invite_view(self):
        """Test the admin invite view logic."""
        url = reverse("invite_user")
        
        # Test GET
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        
        # Test POST (Send Invite)
        response = self.client.post(url, {
            "email": "newuser@example.com",
            "role": "manager"
        })
        
        # Should redirect on success
        self.assertEqual(response.status_code, 302) 
        
        # Check DB
        invite = Invite.objects.filter(email="newuser@example.com").first()
        self.assertIsNotNone(invite)
        self.assertEqual(invite.role, "manager")
        self.assertEqual(invite.organization, self.org)
        self.assertEqual(invite.created_by, self.admin_user)
