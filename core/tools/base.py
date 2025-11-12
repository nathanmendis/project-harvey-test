# core/tools/base.py
from langchain_core.tools import tool
from core.models import Candidate, JobRole, Interview, EmailLog
from core.action_result import ActionResult
from django.utils import timezone

@tool("add_candidate", return_direct=True)
def add_candidate(name: str, email: str, phone: str = "", skills: str = "", source: str = "Chatbot", user=None) -> str:
    """Add a new candidate to the HR system."""
    org = getattr(user, "organization", None)
    if Candidate.objects.filter(email=email, organization=org).exists():
        return f"Candidate '{email}' already exists."

    Candidate.objects.create(
        organization=org,
        name=name,
        email=email,
        phone=phone,
        skills=[s.strip() for s in skills.split(",")] if skills else [],
        source=source,
        status="pending",
    )
    return f"✅ Candidate '{name}' added successfully."


@tool("create_job_description", return_direct=True)
def create_job_description(title: str, description: str, requirements: str, department: str, user=None) -> str:
    """Create a job role in the HR system."""
    org = getattr(user, "organization", None)
    JobRole.objects.create(
        organization=org,
        title=title,
        description=description,
        requirements=requirements,
        department=department,
    )
    return f"💼 Job role '{title}' created successfully."


@tool("schedule_interview", return_direct=True)
def schedule_interview(candidate_id: int, when: str, interviewer_id: int, duration_minutes: int = 30, location_link: str = "", user=None) -> str:
    """Schedule an interview with a candidate."""
    org = getattr(user, "organization", None)
    Interview.objects.create(
        organization=org,
        candidate_id=candidate_id,
        interviewer_id=interviewer_id,
        date_time=when,
        status="scheduled",
    )
    return f"🗓 Interview scheduled for candidate {candidate_id} on {when}."


@tool("send_email", return_direct=True)
def send_email(recipient: str, subject: str, body: str, user=None) -> str:
    """Send (log) an email to a candidate or employee."""
    org = getattr(user, "organization", None)
    EmailLog.objects.create(
        organization=org,
        recipient_email=recipient,
        subject=subject,
        body=body,
        status="sent",
        sent_time=timezone.now(),
    )
    return f"📧 Email sent to {recipient} — subject: {subject}."


@tool("shortlist_candidates", return_direct=True)
def shortlist_candidates(skills: str, limit: int = 5, user=None) -> str:
    """Shortlist candidates based on matching skills."""
    org = getattr(user, "organization", None)
    skills_list = [s.strip().lower() for s in skills.split(",")]
    candidates = Candidate.objects.filter(organization=org)
    matched = [c.name for c in candidates if any(skill in ",".join(c.skills or []) for skill in skills_list)]
    matched = matched[:limit]
    return f"🎯 Shortlisted candidates: {', '.join(matched) if matched else 'none found'}."
