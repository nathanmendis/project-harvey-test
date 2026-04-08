import json
from django.test import TestCase
from unittest.mock import MagicMock, patch
from core.models.organization import Organization, User
from core.models.recruitment import Candidate, JobRole, CandidateJobScore
from core.ai.agentic.tools.recruitment.candidates import shortlist_candidates

class ShortlistCandidateToolTest(TestCase):
    def setUp(self):
        # Setup basic organization and user
        self.org = Organization.objects.create(name="Harvey AI", domain="harvey.ai")
        self.user = User.objects.create_user(
            username="hr_manager", 
            password="testpassword", 
            organization=self.org,
            role="hr"
        )

    def test_shortlist_by_skills_with_data(self):
        """Test shortlisting by skills when candidates exist."""
        # Create some candidates
        Candidate.objects.create(
            organization=self.org,
            name="Alice Python",
            email="alice@python.com",
            skills=["Python", "Django", "Postgres"],
            status="pending"
        )
        Candidate.objects.create(
            organization=self.org,
            name="Bob React",
            email="bob@react.com",
            skills=["React", "Tailwind", "Javascript"],
            status="pending"
        )

        # Call the tool for Python skills
        result_json = shortlist_candidates(skills="Python", user=self.user)
        result = json.loads(result_json)

        self.assertTrue(result["ok"])
        self.assertIn("Alice Python", result["message"])
        self.assertEqual(len(result["results"]), 1)
        self.assertEqual(result["results"][0]["name"], "Alice Python")

    @patch("core.ai.utils.candidate_scorer.CandidateScorer.score_candidate")
    def test_shortlist_by_job_role_with_data(self, mock_score):
        """Test shortlisting by job role with mocked AI scoring."""
        # Create a job role
        job = JobRole.objects.create(
            organization=self.org,
            title="Senior Backend Engineer",
            description="Expert Python dev needed",
            requirements="Python, LangChain",
            department="Engineering"
        )

        # Create candidates
        c1 = Candidate.objects.create(
            organization=self.org,
            name="Expert Dev",
            email="expert@dev.com",
            skills=["Python", "LangChain"],
            status="pending"
        )
        c2 = Candidate.objects.create(
            organization=self.org,
            name="Junior Dev",
            email="junior@dev.com",
            skills=["HTML"],
            status="pending"
        )

        # Mock the scorer: Expert gets 95, Junior gets 10
        mock_score.side_effect = lambda c, j: (95 if c.id == c1.id else 10, "Match info")

        # Call the tool with job_role_id
        result_json = shortlist_candidates(job_role_id=job.id, user=self.user)
        result = json.loads(result_json)

        self.assertTrue(result["ok"])
        self.assertIn("Senior Backend Engineer", result["message"])
        # results should be sorted by score desc
        self.assertEqual(result["results"][0]["name"], "Expert Dev")
        self.assertEqual(result["results"][0]["score"], 95)
        self.assertEqual(result["results"][1]["name"], "Junior Dev")
        self.assertEqual(result["results"][1]["score"], 10)

    def test_shortlist_no_data(self):
        """Test the scenario where no candidates or job roles exist."""
        # Scenario 1: No candidates matching skills
        result_json = shortlist_candidates(skills="React", user=self.user)
        result = json.loads(result_json)
        
        self.assertTrue(result["ok"])
        self.assertIn("None found", result["message"])
        self.assertEqual(len(result["results"]), 0)

        # Scenario 2: Job role does not exist
        result_err_json = shortlist_candidates(job_role_id=999, user=self.user)
        result_err = json.loads(result_err_json)
        
        self.assertFalse(result_err["ok"])
        self.assertIn("not found", result_err["message"])

    def test_shortlist_no_params(self):
        """Test error when no parameters are provided."""
        result_json = shortlist_candidates(user=self.user)
        result = json.loads(result_json)
        
        self.assertFalse(result["ok"])
        self.assertIn("provide either a job_role_id or skills", result["message"])
