# models.py
from django.db import models
from django.contrib.auth.models import AbstractUser



class User(AbstractUser):
    # This is a custom user model.
    # Add your unique fields here if any.
    name = models.CharField(max_length=255)
    role = models.CharField(max_length=50)

    # Add related_name to the groups and user_permissions fields to resolve the clash.
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

# To track each AI conversation.
class Conversation(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)

# To store individual chat messages.
class Message(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE)
    sender = models.CharField(max_length=10) 
    message_text = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

# To store candidate profile info.
class Candidate(models.Model):
    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, null=True, blank=True)
    skills = models.JSONField(null=True, blank=True)
    resume_file = models.FileField(upload_to='resumes/')
    parsed_data = models.JSONField(null=True, blank=True)
    source = models.CharField(max_length=50) 
    status = models.CharField(max_length=50, default='pending')

# To store job postings.
class JobRole(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    requirements = models.TextField()
    department = models.CharField(max_length=255)

# To manage the relationship between a candidate and a job posting.
# This can be a separate model or a ManyToMany relationship on Candidate.
# A separate model gives more flexibility to add additional fields like status, etc.
# The `models.py` file should also have models for your other tools, as listed below.

# To store scheduled interviews.
class Interview(models.Model):
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE)
    interviewer = models.ForeignKey(User, on_delete=models.CASCADE)
    date_time = models.DateTimeField()
    status = models.CharField(max_length=50)
    
# To handle leave requests.
class LeaveRequest(models.Model):
    employee = models.ForeignKey(User, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    leave_type = models.CharField(max_length=50)
    status = models.CharField(max_length=50)

# To track sent emails.
class EmailLog(models.Model):
    recipient_email = models.EmailField()
    subject = models.CharField(max_length=255)
    body = models.TextField()
    sent_time = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=50)

# To store calendar events.
class CalendarEvent(models.Model):
    title = models.CharField(max_length=255)
    participants = models.ManyToManyField(User)
    date_time = models.DateTimeField()
    location_link = models.URLField(max_length=200, null=True, blank=True)

# To store configurations for external HRMS integrations.
class HRMSIntegrationConfig(models.Model):
    hrms_type = models.CharField(max_length=50)
    base_url = models.URLField()
    auth_token = models.CharField(max_length=255)
    is_active = models.BooleanField(default=False)
    # The auth token should be encrypted for security.