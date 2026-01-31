from django.db import models
import uuid
from django.utils import timezone
from .organization import Organization, User

class Invite(models.Model):
    email = models.EmailField()
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="invites")
    role = models.CharField(max_length=50, choices=User.ROLE_CHOICES, default="employee")
    expires_at = models.DateTimeField()
    accepted = models.BooleanField(default=False)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="created_invites")
    created_at = models.DateTimeField(auto_now_add=True)

    def is_valid(self):
        return not self.accepted and self.expires_at > timezone.now()

    def __str__(self):
        return f"Invite for {self.email} ({self.role})"
