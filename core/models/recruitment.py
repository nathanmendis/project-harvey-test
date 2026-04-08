from django.db import models
from .organization import Organization, User

class Candidate(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending Assessment'),
        ('shortlisted', 'Shortlisted'),
        ('interviewing', 'Interviewing'),
        ('offered', 'Offer Extended'),
        ('hired', 'Hired'),
        ('rejected', 'Rejected'),
    ]

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, null=True, blank=True)
    skills = models.JSONField(null=True, blank=True)
    resume_file = models.FileField(upload_to='resumes/')
    parsed_data = models.JSONField(null=True, blank=True)
    source = models.CharField(max_length=50)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='pending')

    def __str__(self):
        return f"{self.name} ({self.organization.name})"


class CandidateJobScore(models.Model):
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name='job_scores')
    job_role = models.ForeignKey('JobRole', on_delete=models.CASCADE, related_name='candidate_scores')
    score = models.FloatField()
    justification = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('candidate', 'job_role')

    def __str__(self):
        return f"{self.candidate.name} - {self.job_role.title}: {self.score}"


class JobRole(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    description = models.TextField()
    requirements = models.TextField()
    department = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.title} - {self.organization.name}"


class Interview(models.Model):
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('pending_feedback', 'Pending Feedback'),
    ]

    TYPE_CHOICES = [
        ('online', 'Online (Google Meet)'),
        ('in_person', 'In-Person'),
    ]

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE)
    interviewer = models.ForeignKey(User, on_delete=models.CASCADE)
    date_time = models.DateTimeField()
    interview_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='online')
    location = models.CharField(max_length=255, null=True, blank=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='scheduled')
    description = models.TextField(null=True, blank=True)
   
    def __str__(self):
        return f"Interview: {self.candidate.name} ({self.organization.name})"



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
    duration_minutes = models.PositiveIntegerField(default=60)
    location_link = models.URLField(max_length=200, null=True, blank=True)

    def __str__(self):
        return f"{self.title} ({self.organization.name})"


from encrypted_model_fields.fields import EncryptedCharField 

class HRMSSystemConfig(models.Model):
    organization = models.OneToOneField("Organization", on_delete=models.CASCADE, related_name="hrms_system_config")
    hrms_type = models.CharField(max_length=50, default='harvey')
    is_active = models.BooleanField(default=True)
    
    # Encrypted Credentials
    base_url = models.URLField(help_text="Base URL for the HRMS API")
    auth_token = EncryptedCharField(max_length=255, help_text="Encrypted API Access Token")
    
    # Dynamic Endpoints Map
    departments_endpoint = models.CharField(max_length=255, default="/api/v1/departments")
    employees_endpoint = models.CharField(max_length=255, default="/api/v1/employees")
    jobs_endpoint = models.CharField(max_length=255, default="/api/v1/jobs")
    candidates_endpoint = models.CharField(max_length=255, default="/api/v1/candidates")
    interviews_endpoint = models.CharField(max_length=255, default="/api/v1/interviews")
    onboarding_endpoint = models.CharField(max_length=255, default="/api/v1/onboarding")

    # Security Validation
    edit_token = models.CharField(max_length=64, null=True, blank=True)
    edit_token_expires_at = models.DateTimeField(null=True, blank=True)

    def generate_edit_token(self):
        """Generates a secure 16-character token valid for 24 hours."""
        from django.utils import timezone
        import secrets
        import string
        
        characters = string.ascii_letters + string.digits
        self.edit_token = ''.join(secrets.choice(characters) for _ in range(16))
        self.edit_token_expires_at = timezone.now() + timezone.timedelta(days=1)
        self.save()
        return self.edit_token

    def __str__(self):
        return f"{self.hrms_type} Config ({self.organization.name})"


class HRMSEndpointMapping(models.Model):
    """Stores a dynamic mapping from an external API endpoint to an internal Harvey model."""

    TARGET_MODEL_CHOICES = [
        ('Employee', 'Employee'),
        ('Candidate', 'Candidate'),
        ('Interview', 'Interview'),
        ('LeaveRequest', 'Leave Request'),
        ('JobRole', 'Job Role'),
    ]

    hrms_config = models.ForeignKey(
        HRMSSystemConfig,
        on_delete=models.CASCADE,
        related_name='endpoint_mappings'
    )
    endpoint_url = models.CharField(
        max_length=255,
        help_text="Relative path of the external API, e.g. /api/v2/leaves"
    )
    target_model = models.CharField(
        max_length=50,
        choices=TARGET_MODEL_CHOICES,
        help_text="Harvey model to sync the data into"
    )
    # Stored sample JSON the user pasted for validation
    sample_json = models.TextField(
        null=True, blank=True,
        help_text="Raw JSON sample response used for compatibility validation"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('hrms_config', 'endpoint_url')

    def __str__(self):
        return f"{self.target_model} ← {self.endpoint_url}"



