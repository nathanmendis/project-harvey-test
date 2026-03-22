from django.db import models
from .organization import Organization, User

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
    is_deducted = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.employee.username} - {self.leave_type} ({self.status})"

class OrganizationLeavePolicy(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='leave_policies')
    year = models.IntegerField()
    leave_type = models.CharField(max_length=50)
    default_allocated = models.FloatField(default=0.0)

    class Meta:
        unique_together = ('organization', 'year', 'leave_type')

    def __str__(self):
        return f"{self.organization.name} - {self.year} - {self.leave_type} ({self.default_allocated} days)"

class LeaveBalance(models.Model):
    employee = models.ForeignKey(User, on_delete=models.CASCADE, related_name='leave_balances')
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    year = models.IntegerField()
    leave_type = models.CharField(max_length=50)
    total_allocated = models.FloatField(default=0.0)
    used = models.FloatField(default=0.0)

    class Meta:
        unique_together = ('employee', 'year', 'leave_type')

    @property
    def remaining(self):
        return self.total_allocated - self.used

    def __str__(self):
        return f"{self.employee.username} - {self.year} {self.leave_type} (Used: {self.used}/{self.total_allocated})"

class LeaveSystemConfig(models.Model):
    organization = models.OneToOneField("Organization", on_delete=models.CASCADE, related_name="leave_system_config")
    edit_token = models.CharField(max_length=64, null=True, blank=True)
    edit_token_expires_at = models.DateTimeField(null=True, blank=True)

    def generate_edit_token(self):
        from django.utils import timezone
        import secrets
        import string
        characters = string.ascii_letters + string.digits
        self.edit_token = ''.join(secrets.choice(characters) for _ in range(16))
        self.edit_token_expires_at = timezone.now() + timezone.timedelta(days=1)
        self.save()
        return self.edit_token

    def __str__(self):
        return f"Leave Config ({self.organization.name})"
