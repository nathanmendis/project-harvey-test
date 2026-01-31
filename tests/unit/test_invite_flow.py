import pytest
from core.models.invite import Invite
from core.models.organization import User, Organization
from django.utils import timezone
from datetime import timedelta
from django.urls import reverse
from django.test import Client

@pytest.mark.django_db
def test_invite_model_creation():
    """Test that an invite can be created and is valid."""
    org = Organization.objects.create(name="Test Org")
    admin_user = User.objects.create_user(username="admin", password="password", organization=org)
    
    invite = Invite.objects.create(
        email="test@example.com",
        organization=org,
        role="employee",
        expires_at=timezone.now() + timedelta(days=7),
        created_by=admin_user
    )
    
    assert invite.token is not None
    assert invite.is_valid()
    assert invite.role == "employee"
    assert invite.email == "test@example.com"

@pytest.mark.django_db
def test_invite_expiration():
    """Test that expired invites are invalid."""
    org = Organization.objects.create(name="Test Org")
    
    invite = Invite.objects.create(
        email="expired@example.com",
        organization=org,
        expires_at=timezone.now() - timedelta(days=1)
    )
    
    assert not invite.is_valid()

@pytest.mark.django_db
def test_admin_invite_view():
    """Test the admin invite view logic."""
    # Setup
    org = Organization.objects.create(name="Test Org")
    admin_user = User.objects.create_user(username="admin", password="password", organization=org, role="org_admin")
    client = Client()
    client.force_login(admin_user)
    
    url = reverse("invite_user")
    
    # Test GET
    response = client.get(url)
    assert response.status_code == 200
    
    # Test POST (Send Invite)
    response = client.post(url, {
        "email": "newuser@example.com",
        "role": "manager"
    })
    
    # Should redirect on success
    assert response.status_code == 302 
    
    # Check DB
    invite = Invite.objects.filter(email="newuser@example.com").first()
    assert invite is not None
    assert invite.role == "manager"
    assert invite.organization == org
    assert invite.created_by == admin_user
