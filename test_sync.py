import os
import django
import logging

# Setup django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project_harvey.settings')
django.setup()

logging.basicConfig(level=logging.INFO)

from core.models.organization import Organization
from core.models.recruitment import HRMSSystemConfig, Candidate
from core.models.organization import User
from integrations.hrms.sync.tasks import sync_organization_data

print("Before sync - Candidates:", Candidate.objects.count())
print("Before sync - Users:", User.objects.count())

org = Organization.objects.first()
if not org:
    org = Organization.objects.create(name="Test Organization", description="Testing integration syncing")

# Ensure integration config exists
config, created = HRMSSystemConfig.objects.update_or_create(
    organization=org,
    defaults={
        'hrms_type': 'harvey',
        'is_active': True,
        'base_url': 'http://localhost:8001',
        'auth_token': 'harvey-secret-token',
        'departments_endpoint': '/api/v1/departments',
        'employees_endpoint': '/api/v1/employees',
        'jobs_endpoint': '/api/v1/jobs',
        'candidates_endpoint': '/api/v1/candidates',
        'interviews_endpoint': '/api/v1/interviews',
        'onboarding_endpoint': '/api/v1/onboarding',
    }
)

print("\n--- Triggering HRMS Sync Data ---")
try:
    sync_organization_data(org.id)
    print("Sync successful!")
except Exception as e:
    import traceback
    traceback.print_exc()
    print(f"Sync failed (expected if mock server is down): {e}")

print("After sync - Candidates:", Candidate.objects.count())
print("After sync - Users:", User.objects.count())
