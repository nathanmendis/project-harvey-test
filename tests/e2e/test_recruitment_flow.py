import os
from django.test import TestCase
from django.utils import timezone
from unittest.mock import MagicMock, patch
import json
from core.models.organization import Organization, User
from core.models.recruitment import JobRole, Candidate, Interview, EmailLog, CandidateJobScore
from core.tools.recruitment_tools import (
    create_job_description,
    add_candidate_with_resume,
    shortlist_candidates,
    schedule_interview,
    send_email
)

class RecruitmentFlowTest(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="Tech Corp")
        self.user = User.objects.create_user(username="hr_manager", password="password", organization=self.org)
        
        # Dummy Resume
        self.resume_path = "test_resume.pdf"
        with open(self.resume_path, "w") as f:
            f.write("Dummy PDF content.")

    def tearDown(self):
        if os.path.exists(self.resume_path):
            os.remove(self.resume_path)
            
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT pg_terminate_backend(pid) 
                FROM pg_stat_activity 
                WHERE datname = current_database() 
                AND pid <> pg_backend_pid();
            """)

    @patch("core.services.resume_parser.ResumeParser.parse")
    @patch("core.llm_graph.tools_registry.get_reasoner_llm")
    @patch("core.signals.ModelIndexer") 
    def test_end_to_end_recruitment(self, mock_indexer, mock_get_llm, mock_parse):
        # --- Mocks Setup ---
        mock_parse.return_value = "John Doe\nPython Developer\nSkills: Python, Django, DRF"
        
        # Mock LLM for Shortlisting
        mock_llm = MagicMock()
        mock_get_llm.return_value = mock_llm
        
        def scoring_side_effect(messages):
            # Simulate high score for John Doe
            return MagicMock(content='{"score": 95, "justification": "Perfect match"}')
        mock_llm.invoke.side_effect = scoring_side_effect

        print("\n--- Starting Recruitment Flow E2E ---")

        # 1. Create Job
        print("1. Creating Job...")
        res_job = create_job_description.func(
            title="Senior Python Dev",
            description="Expert needed",
            requirements="Python, Django",
            department="Eng",
            user=self.user
        )
        print(f"Result: {res_job}")
        self.assertIn("I've created the new job role", res_job)
        job = JobRole.objects.get(title="Senior Python Dev")
        
        # 2. Add Candidate via Resume
        print("2. Adding Candidate (Resume)...")
        res_cand = add_candidate_with_resume.func(
            file_path=self.resume_path,
            email="john.doe@example.com",
            name="John Doe",
            user=self.user
        )
        self.assertIn("I've successfully added", res_cand)
        candidate = Candidate.objects.get(email="john.doe@example.com")
        self.assertEqual(candidate.parsed_data, "John Doe\nPython Developer\nSkills: Python, Django, DRF")

        # 3. Shortlist Candidates
        print("3. Shortlisting...")
        res_shortlist = shortlist_candidates.func(
            job_role_id=job.id,
            user=self.user
        )
        print(f"Shortlist Result: {res_shortlist}")
        data = json.loads(res_shortlist)
        self.assertTrue(data.get("ok"))
        results = data.get("results", [])
        self.assertTrue(len(results) > 0)
        self.assertEqual(results[0]["name"], "John Doe")
        self.assertEqual(results[0]["score"], 95)

        # 4. Schedule Interview
        print("4. Scheduling Interview...")
        interview_time = (timezone.now() + timezone.timedelta(days=2)).isoformat()
        res_interview = schedule_interview.func(
            candidate=candidate.email,  # Pass email as 'candidate' string
            start_time=interview_time,  # 'when' -> 'start_time'
            user=self.user
        )
        print(f"Interview Result: {res_interview}")
        data_i = json.loads(res_interview)
        self.assertIn("confirmed that the interview", data_i.get("message"))
        self.assertTrue(Interview.objects.filter(candidate=candidate, status="scheduled").exists())

        # 5. Send Offer/Email
        print("5. Sending Email...")
        res_email = send_email.func(
            recipient=candidate.email,
            subject="You're Hired!",
            body="Welcome aboard.",
            user=self.user
        )
        print(f"Email Result: {res_email}")
        data_e = json.loads(res_email)
        self.assertTrue(data_e.get("ok"))
        self.assertIn("I've sent the email to", data_e.get("message"))
        self.assertTrue(EmailLog.objects.filter(recipient_email=candidate.email, status="sent").exists())
        
        print("--- Recruitment Flow Passed ---")
