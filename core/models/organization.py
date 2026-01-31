from django.db import models
from django.contrib.auth.models import AbstractUser
import uuid

def generate_org_id():
    return f"ORG-{uuid.uuid4().hex[:8].upper()}"

class Organization(models.Model):
    org_id = models.CharField(
        max_length=50,
        unique=True,
        default=generate_org_id,  
        editable=False
    )
    name = models.CharField(max_length=255)
    domain = models.CharField(max_length=100, unique=True, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.org_id})"

class User(AbstractUser):
    ROLE_CHOICES = [
        ("employee", "Employee"),
        ("manager", "Manager"),
        ("hr", "HR"),
        ("org_admin", "Organization Admin"),
    ]

    name = models.CharField(max_length=255)
    role = models.CharField(max_length=50, choices=ROLE_CHOICES, default="employee")
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="users", null=True, blank=True
    )
    has_chat_access = models.BooleanField(default=True)
    
    def is_org_admin(self):
        """Helper to check if user is an organization-level admin."""
        return self.role == "org_admin"

    def __str__(self):
        org = self.organization.name if self.organization else "No Org"
        return f"{self.username} ({org})"
