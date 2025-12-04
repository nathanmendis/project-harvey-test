from django.test import TestCase
import json
from core.tools.base import add_candidate, create_job_description
from core.models.recruitment import Candidate, JobRole
from core.models.organization import Organization

class ToolRobustnessTest(TestCase):
    def test_add_candidate_no_user(self):
        """Test add_candidate returns error without a user."""
        # Ensure no orgs exist initially
        Organization.objects.all().delete()
        
        result_json = add_candidate.invoke({
            "name": "Fallback User",
            "email": "fallback@example.com",
            "skills": "Testing",
            "phone": "1234567890"
        })
        
        result = json.loads(result_json)
        self.assertFalse(result["ok"])
        self.assertIn("User is not associated with any organization", result["message"])
        
        # Verify NO org was created
        self.assertFalse(Organization.objects.filter(name="Demo Corp").exists())

    def test_create_job_description_no_user(self):
        """Test create_job_description returns error without a user."""
        # Create a default org first (should be ignored if user not linked)
        Organization.objects.create(name="Existing Org")
        
        result_json = create_job_description.invoke({
            "title": "Test Role",
            "description": "Test Desc",
            "requirements": "None",
            "department": "Engineering"
        })
        
        result = json.loads(result_json)
        self.assertFalse(result["ok"])
        self.assertIn("User is not associated with any organization", result["message"])
