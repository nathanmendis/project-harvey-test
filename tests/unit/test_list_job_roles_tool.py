import json
from django.test import TestCase
from core.models.organization import Organization, User
from core.models.recruitment import JobRole
from core.ai.agentic.tools.recruitment.jobs import list_job_roles

class ListJobRolesToolTest(TestCase):
    def setUp(self):
        # Setup basic organization and user
        self.org = Organization.objects.create(name="Harvey AI", domain="harvey.ai")
        self.user = User.objects.create_user(
            username="hr_manager", 
            password="testpassword", 
            organization=self.org,
            role="hr"
        )

    def test_list_job_roles_empty(self):
        """Test list_job_roles when no roles exist."""
        result_json = list_job_roles.func(user=self.user)
        result = json.loads(result_json)
        self.assertTrue(result["ok"])
        self.assertEqual(result["message"], "No job roles found.")
        self.assertEqual(len(result.get("results", [])), 0)

    def test_list_job_roles_success(self):
        """Test listing existing job roles."""
        JobRole.objects.create(
            organization=self.org,
            title="Python Developer",
            description="Django backend",
            requirements="Python, Django",
            department="Engineering"
        )
        JobRole.objects.create(
            organization=self.org,
            title="Product Designer",
            description="UI/UX",
            requirements="Figma",
            department="Design"
        )

        result_json = list_job_roles.func(user=self.user)
        result = json.loads(result_json)
        
        self.assertTrue(result["ok"])
        self.assertIn("Python Developer", result["message"])
        self.assertIn("Product Designer", result["message"])
        self.assertEqual(len(result["results"]), 2)

    def test_list_job_roles_filter_department(self):
        """Test listing job roles with department filter."""
        JobRole.objects.create(
            organization=self.org,
            title="Python Developer",
            description="Django backend",
            requirements="Python, Django",
            department="Engineering"
        )
        JobRole.objects.create(
            organization=self.org,
            title="Product Designer",
            description="UI/UX",
            requirements="Figma",
            department="Design"
        )

        result_json = list_job_roles.func(department="Engineering", user=self.user)
        result = json.loads(result_json)
        
        self.assertTrue(result["ok"])
        self.assertIn("Python Developer", result["message"])
        self.assertNotIn("Product Designer", result["message"])
        self.assertEqual(len(result["results"]), 1)
        self.assertEqual(result["results"][0]["title"], "Python Developer")

    def test_list_job_roles_filter_title(self):
        """Test listing job roles with title filter."""
        JobRole.objects.create(
            organization=self.org,
            title="Python Developer",
            description="Django backend",
            requirements="Python, Django",
            department="Engineering"
        )
        JobRole.objects.create(
            organization=self.org,
            title="Product Designer",
            description="UI/UX",
            requirements="Figma",
            department="Design"
        )

        result_json = list_job_roles.func(title="Product", user=self.user)
        result = json.loads(result_json)
        
        self.assertTrue(result["ok"])
        self.assertNotIn("Python Developer", result["message"])
        self.assertIn("Product Designer", result["message"])
        self.assertEqual(len(result["results"]), 1)
        self.assertEqual(result["results"][0]["title"], "Product Designer")

    def test_list_job_roles_no_org(self):
        """Test error when user has no organization."""
        user_no_org = User.objects.create_user(
            username="stray_user", 
            password="testpassword"
        )
        result_json = list_job_roles.func(user=user_no_org)
        result = json.loads(result_json)
        self.assertFalse(result["ok"])
        self.assertIn("User not in organization", result["message"])
