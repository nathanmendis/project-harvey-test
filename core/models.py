from django.db import models
from django.contrib.auth.models import AbstractUser
import uuid
def generate_org_id():
    import uuid
    return f"ORG-{uuid.uuid4().hex[:8].upper()}"



# ORGANIZATION MODEL (Top-level tenant)

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


# CUSTOM USER MODEL

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

    groups = models.ManyToManyField(
        'auth.Group',
        related_name='core_user_set',
        blank=True,
        help_text='The groups this user belongs to.',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='core_user_set',
        blank=True,
        help_text='Specific permissions for this user.',
    )

    def is_org_admin(self):
        """Helper to check if user is an organization-level admin."""
        return self.role == "org_admin"

    def __str__(self):
        org = self.organization.name if self.organization else "No Org"
        return f"{self.username} ({org})"
    


    
# AI CHAT MODELS

class Conversation(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    user = models.ForeignKey('User', on_delete=models.CASCADE)
    title = models.CharField(max_length=255, default="New Chat")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    context_state = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return f"{self.title} ({self.user.username})"


class Message(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE)
    sender = models.CharField(max_length=10)  # 'user' or 'ai'
    message_text = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.sender.capitalize()} → {self.message_text[:40]}"


# HR MODELS

class Candidate(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, null=True, blank=True)
    skills = models.JSONField(null=True, blank=True)
    resume_file = models.FileField(upload_to='resumes/')
    parsed_data = models.JSONField(null=True, blank=True)
    source = models.CharField(max_length=50)
    status = models.CharField(max_length=50, default='pending')

    def __str__(self):
        return f"{self.name} ({self.organization.name})"


class JobRole(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    description = models.TextField()
    requirements = models.TextField()
    department = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.title} - {self.organization.name}"


class Interview(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE)
    interviewer = models.ForeignKey(User, on_delete=models.CASCADE)
    date_time = models.DateTimeField()
    status = models.CharField(max_length=50)

    def __str__(self):
        return f"Interview: {self.candidate.name} ({self.organization.name})"


class LeaveRequest(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    employee = models.ForeignKey(User, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    leave_type = models.CharField(max_length=50)
    status = models.CharField(max_length=50)

    def __str__(self):
        return f"{self.employee.username} - {self.leave_type} ({self.status})"


class EmailLog(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    recipient_email = models.EmailField()
    subject = models.CharField(max_length=255)
    body = models.TextField()
    sent_time = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=50)

    def __str__(self):
        return f"Email to {self.recipient_email} ({self.organization.name})"


class CalendarEvent(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    participants = models.ManyToManyField(User)
    date_time = models.DateTimeField()
    location_link = models.URLField(max_length=200, null=True, blank=True)

    def __str__(self):
        return f"{self.title} ({self.organization.name})"


class HRMSIntegrationConfig(models.Model):
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="hrms_configs"
    )
    hrms_type = models.CharField(max_length=50)
    base_url = models.URLField()
    auth_token = models.CharField(max_length=255)
    is_active = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.hrms_type} Config ({self.organization.name})"
