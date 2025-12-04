import os
import django
import sys
import json
from django.utils import timezone

# Setup Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project_harvey.settings')
django.setup()

from core.models.organization import User, Organization
from core.models.recruitment import Candidate, JobRole, Interview, EmailLog
from core.tools.base import (
    add_candidate,
    create_job_description,
    schedule_interview,
    send_email,
    shortlist_candidates
)

def test_tools_db_updates():
    print("🚀 Starting Tool & DB Verification...")
    
    # 1. Setup Test Data
    org_name = "ToolTest Org"
    org, _ = Organization.objects.get_or_create(name=org_name)
    user, _ = User.objects.get_or_create(username="tool_tester", organization=org)
    
    # Cleanup previous test data
    Candidate.objects.filter(organization=org).delete()
    JobRole.objects.filter(organization=org).delete()
    Interview.objects.filter(organization=org).delete()
    EmailLog.objects.filter(organization=org).delete()

    print(f"✅ Setup complete for Org: {org_name}")

    # 2. Test add_candidate
    print("\n🧪 Testing add_candidate...")
    # Tools decorated with @tool are StructuredTool objects. 
    # We can call them via .invoke() or access the underlying function via .func if we want to bypass validation/parsing,
    # but .invoke() expects a dict. Since we want to test the python logic directly with the user argument,
    # we should use the underlying function which is stored in .func or just call it if it wasn't decorated (but it is).
    # Actually, langchain tools when called as functions might behave differently. 
    # Let's use the .func attribute to call the original python function directly.
    
    res = add_candidate.func(
        name="Alice Tool", 
        email="alice@tool.test", 
        skills="python, testing", 
        phone="1234567890", 
        user=user
    )
    print(f"Result: {res}")
    
    candidate = Candidate.objects.filter(email="alice@tool.test", organization=org).first()
    if candidate:
        print(f"✅ DB Verified: Candidate '{candidate.name}' created with ID {candidate.id}")
    else:
        print("❌ DB Failure: Candidate not found!")

    # 3. Test create_job_description
    print("\n🧪 Testing create_job_description...")
    res = create_job_description.func(
        title="Senior Tester", 
        description="Test everything", 
        requirements="Python, Django", 
        department="QA", 
        user=user
    )
    print(f"Result: {res}")
    
    job = JobRole.objects.filter(title="Senior Tester", organization=org).first()
    if job:
        print(f"✅ DB Verified: Job '{job.title}' created with ID {job.id}")
    else:
        print("❌ DB Failure: Job not found!")

    # 4. Test schedule_interview
    print("\n🧪 Testing schedule_interview...")
    if candidate:
        when = timezone.now().isoformat()
        res = schedule_interview.func(
            candidate_id=candidate.id, 
            when=when, 
            interviewer_id=user.id, 
            user=user
        )
        print(f"Result: {res}")
        
        interview = Interview.objects.filter(candidate=candidate, organization=org).first()
        if interview:
            print(f"✅ DB Verified: Interview scheduled for {interview.date_time}")
        else:
            print("❌ DB Failure: Interview not found!")
    else:
        print("⚠️ Skipping interview test (no candidate)")

    # 5. Test send_email
    print("\n🧪 Testing send_email...")
    res = send_email.func(
        recipient="alice@tool.test", 
        subject="Hello", 
        body="Welcome!", 
        user=user
    )
    print(f"Result: {res}")
    
    email_log = EmailLog.objects.filter(recipient_email="alice@tool.test", organization=org).first()
    if email_log:
        print(f"✅ DB Verified: Email log found for {email_log.recipient_email}")
    else:
        print("❌ DB Failure: Email log not found!")

    # 6. Test shortlist_candidates
    print("\n🧪 Testing shortlist_candidates...")
    res = shortlist_candidates.func(skills="python", user=user)
    data = json.loads(res)
    if data.get("ok") and len(data.get("results", [])) > 0:
        print(f"✅ Logic Verified: Shortlisted {len(data['results'])} candidates.")
    else:
        print(f"❌ Logic Failure: Failed to shortlist. Response: {res}")

if __name__ == "__main__":
    test_tools_db_updates()
