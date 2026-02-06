from django.db import models
from .organization import Organization, User

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
    LEAVE_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
    ]
    status = models.CharField(max_length=50, choices=LEAVE_STATUS_CHOICES, default='pending')

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
    duration_minutes = models.PositiveIntegerField(default=60)
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
