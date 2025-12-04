import json
from django.utils.dateparse import parse_datetime
from django.utils import timezone
from langchain_core.tools import tool
from core.models.recruitment import Candidate, JobRole, Interview, EmailLog

def ok(message, **data):
    return json.dumps({"ok": True, "message": message, **data})

def err(message):
    return json.dumps({"ok": False, "message": message})


@tool("add_candidate", return_direct=True)
def add_candidate(name: str, email: str, skills: str, phone: str, source: str = "Chatbot", user=None) -> str:
    """Adds a new candidate to your organization's HR system."""
    org = getattr(user, "organization", None)
    if Candidate.objects.filter(email=email, organization=org).exists():
        return err(f"Candidate '{email}' already exists.")

    c = Candidate.objects.create(
        organization=org,
        name=name,
        email=email,
        phone=phone,
        skills=[s.strip() for s in skills.split(",")] if skills else [],
        source=source,
        status="pending",
    )
    return ok(f"Candidate '{name}' added successfully.", id=c.id, name=name)


@tool("create_job_description", return_direct=True)
def create_job_description(title: str, description: str, requirements: str, department: str, user=None) -> str:
    """Creates a job posting / role for hiring."""
    org = getattr(user, "organization", None)
    j = JobRole.objects.create(
        organization=org,
        title=title,
        description=description,
        requirements=requirements,
        department=department,
    )
    return ok(f"Job role '{title}' created successfully.", id=j.id, title=title)


@tool("schedule_interview", return_direct=True)
def schedule_interview(candidate_id: int, when: str, interviewer_id: int, duration_minutes: int = 30, location_link: str = "", user=None) -> str:
    """Schedules a job interview."""
    org = getattr(user, "organization", None)
    dt = parse_datetime(when)
    if not dt:
        return err("Invalid date format. Use ISO 8601 datetime.")

    i = Interview.objects.create(
        organization=org,
        candidate_id=candidate_id,
        interviewer_id=interviewer_id,
        date_time=dt,
        status="scheduled",
    )
    return ok("Interview scheduled.", interview_id=i.id, when=str(dt))


@tool("send_email", return_direct=True)
def send_email(recipient: str, subject: str, body: str, user=None) -> str:
    """Logs a sent email to a candidate or employee."""
    org = getattr(user, "organization", None)
    e = EmailLog.objects.create(
        organization=org,
        recipient_email=recipient,
        subject=subject,
        body=body,
        status="sent",
        sent_time=timezone.now(),
    )
    return ok(f"Email sent to {recipient}", log_id=e.id)


@tool("shortlist_candidates", return_direct=True)
def shortlist_candidates(skills: str, limit: int = 5, user=None) -> str:
    """Shortlists candidates based on matching skills."""
    org = getattr(user, "organization", None)
    skills_list = [s.strip().lower() for s in skills.split(",")]
    candidates = Candidate.objects.filter(organization=org)

    matched = [
        {"id": c.id, "name": c.name}
        for c in candidates
        if any(skill in (",".join(c.skills or [])).lower() for skill in skills_list)
    ]
    matched = matched[:limit]

    msg = f"Shortlisted: {', '.join(c['name'] for c in matched) or 'none'}."
    return ok(msg, results=matched)
