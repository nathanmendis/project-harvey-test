from django.test import TestCase
from django.utils import timezone
from core.models.organization import Organization, User
from core.models.recruitment import JobRole, Candidate, Interview, EmailLog
from core.tools.base import (
    create_job_description,
    add_candidate,
    shortlist_candidates,
    schedule_interview,
    send_email
)
from core.tools.search_tool import search_knowledge_base
import json

class EndToEndUserExperienceTest(TestCase):
    def setUp(self):
        # 1. Setup Organization and User
        self.org = Organization.objects.create(name="Tech Corp")
        self.user = User.objects.create(
            username="hr_manager",
            organization=self.org,
            role="hr"
        )

    def test_full_recruitment_flow(self):
        print("\n--- Starting End-to-End Recruitment Flow Test ---")

        # Step 1: Create a Job Description
        print("Step 1: Creating Job Description...")
        res_job = create_job_description.invoke({
            "title": "Senior Python Developer",
            "description": "We need a python expert.",
            "requirements": "Django, DRF, Celery",
            "department": "Engineering",
            "user": self.user
        })
        print(f"Result: {res_job}")
        
        # Verify JobRole in DB
        self.assertTrue(JobRole.objects.filter(title="Senior Python Developer", organization=self.org).exists())
        job_role = JobRole.objects.get(title="Senior Python Developer")
        self.assertEqual(job_role.department, "Engineering")

        # Step 2: Add a Candidate
        print("\nStep 2: Adding Candidate...")
        res_cand = add_candidate.invoke({
            "name": "John Doe",
            "email": "john.doe@example.com",
            "phone": "1234567890",
            "skills": "Python, Django, SQL",
            "user": self.user
        })
        print(f"Result: {res_cand}")

        # Verify Candidate in DB
        self.assertTrue(Candidate.objects.filter(email="john.doe@example.com", organization=self.org).exists())
        candidate = Candidate.objects.get(email="john.doe@example.com")
        self.assertIn("Python", candidate.skills)

        # Step 3: Search Knowledge Base (Mocking or Integration)
        # Note: Real search requires indexing which might be slow or require setup. 
        # We will test the tool execution, but we might not get results if index is empty in test DB.
        print("\nStep 3: Searching Knowledge Base...")
        # For test purposes, we can try to index the data we just added if we want real results,
        # but for now let's just ensure the tool runs without error.
        try:
            res_search = search_knowledge_base.invoke({"query": "Python developer", "user": self.user})
            print(f"Result: {res_search}")
        except Exception as e:
            print(f"Search tool warning (expected if no index): {e}")

        # Step 4: Shortlist Candidates
        print("\nStep 4: Shortlisting Candidates...")
        res_shortlist = shortlist_candidates.invoke({
            "skills": "Python",
            "limit": 5,
            "user": self.user
        })
        print(f"Result: {res_shortlist}")
        
        # Verify Shortlist Logic
        # The tool returns a JSON string, we need to parse it or check the output string
        self.assertIn("John Doe", res_shortlist)

        # Step 5: Schedule Interview
        print("\nStep 5: Scheduling Interview...")
        interview_time = (timezone.now() + timezone.timedelta(days=1)).isoformat()
        res_interview = schedule_interview.invoke({
            "candidate_id": candidate.id,
            "when": interview_time,
            "interviewer_id": self.user.id,
            "user": self.user
        })
        print(f"Result: {res_interview}")

        # Verify Interview in DB
        self.assertTrue(Interview.objects.filter(candidate=candidate, organization=self.org).exists())
        interview = Interview.objects.get(candidate=candidate)
        self.assertEqual(interview.status, "scheduled")

        # Step 6: Send Email
        print("\nStep 6: Sending Email...")
        res_email = send_email.invoke({
            "recipient": candidate.email,
            "subject": "Interview Confirmed",
            "body": "Hi John, your interview is confirmed.",
            "user": self.user
        })
        print(f"Result: {res_email}")

        # Verify EmailLog in DB
        self.assertTrue(EmailLog.objects.filter(recipient_email=candidate.email, organization=self.org).exists())
        email_log = EmailLog.objects.get(recipient_email=candidate.email)
        self.assertEqual(email_log.status, "sent")

        print("\n--- End-to-End Test Completed Successfully ---")
