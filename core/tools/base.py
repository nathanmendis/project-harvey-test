import json
from django.utils.dateparse import parse_datetime
from django.utils import timezone
from langchain_core.tools import tool
from core.models.recruitment import Candidate, JobRole, Interview, EmailLog, CandidateJobScore
from core.models.organization import Organization
from core.services.resume_parser import ResumeParser
from core.services.candidate_scorer import CandidateScorer

def ok(message, **data):
    return json.dumps({"ok": True, "message": message, **data})

def err(message):
    return json.dumps({"ok": False, "message": message})

def get_org(user):
    """Helper to get organization from user."""
    if user and getattr(user, "organization", None):
        return user.organization
    return None

@tool("add_candidate", return_direct=True)
def add_candidate(name: str, email: str, skills: str, phone: str, source: str = "Chatbot", user=None) -> str:
    """Adds a new candidate to your organization's HR system."""
    org = get_org(user)
    if not org:
        return err("User is not associated with any organization. Please contact support.")

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

import os

@tool("add_candidate_with_resume", return_direct=True)
def add_candidate_with_resume(file_path: str, name: str = "", email: str = "", phone: str = "", user=None) -> str:
    """
    Adds a candidate by parsing their resume (PDF/DOCX).
    If name/email are not provided, tries to extract them (simplified).
    """
    org = get_org(user)
    if not org:
        return err("User is not associated with any organization. Please contact support.")

    # Fix: Resolve file path if it's just a filename
    if not os.path.exists(file_path):
        # Try finding it in 'resumes' folder
        potential_path = os.path.join("resumes", os.path.basename(file_path))
        if os.path.exists(potential_path):
            file_path = potential_path
        else:
            # Try absolute path fallback (user's project root)
            base_dir = r"d:\Code\project_harvey\project-harvey-test"
            potential_path_2 = os.path.join(base_dir, "resumes", os.path.basename(file_path))
            if os.path.exists(potential_path_2):
                file_path = potential_path_2

    parser = ResumeParser()
    try:
        text = parser.parse(file_path)
    except Exception as e:
        return err(f"Failed to parse resume: {e}")

    # Simple extraction fallback if not provided (in real app, use LLM here too)
    # For now, we assume the user provides basic details or we just create with what we have.
    # If email is missing, we can't check uniqueness easily, so we require email or generate a placeholder.
    if not email:
        return err("Please provide the candidate's email address along with the resume.")
    
    if Candidate.objects.filter(email=email, organization=org).exists():
        return err(f"Candidate '{email}' already exists.")

    c = Candidate.objects.create(
        organization=org,
        name=name or "Unknown Candidate",
        email=email,
        phone=phone,
        skills=[], # Skills will be extracted/scored later or we could extract now
        resume_file=file_path, # Storing local path for now, ideally upload to storage
        parsed_data=text,
        source="Resume Upload",
        status="pending",
    )
    
    return ok(f"Candidate '{c.name}' added with resume.", id=c.id, name=c.name)


@tool("create_job_description", return_direct=True)
def create_job_description(title: str, description: str, requirements: str, department: str, user=None) -> str:
    """Creates a job posting / role for hiring."""
    org = get_org(user)
    if not org:
        return err("User is not associated with any organization. Please contact support.")

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
    org = get_org(user)
    if not org:
        return err("User is not associated with any organization. Please contact support.")

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
    org = get_org(user)
    if not org:
        return err("User is not associated with any organization. Please contact support.")

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
def shortlist_candidates(skills: str = "", job_role_id: int = None, limit: int = 5, user=None) -> str:
    """
    Shortlists candidates. 
    If job_role_id is provided, scores candidates against that role.
    Otherwise, filters by skills.
    """
    org = get_org(user)
    if not org:
        return err("User is not associated with any organization. Please contact support.")

    candidates = Candidate.objects.filter(organization=org)
    scored_results = []

    if job_role_id:
        try:
            job_role = JobRole.objects.get(id=job_role_id, organization=org)
            scorer = CandidateScorer()
            
            for c in candidates:
                # Check if score exists
                score_obj = CandidateJobScore.objects.filter(candidate=c, job_role=job_role).first()
                if score_obj:
                    score = score_obj.score
                    justification = score_obj.justification
                else:
                    # Compute score
                    score, justification = scorer.score_candidate(c, job_role)
                
                scored_results.append({
                    "id": c.id,
                    "name": c.name,
                    "score": score,
                    "justification": justification
                })
            
            # Sort by score desc
            scored_results.sort(key=lambda x: x["score"], reverse=True)
            scored_results = scored_results[:limit]
            
            msg = f"Top {len(scored_results)} candidates for '{job_role.title}':"
            return ok(msg, results=scored_results)

        except JobRole.DoesNotExist:
            return err(f"Job Role with ID {job_role_id} not found.")
        except Exception as e:
            return err(f"Error scoring candidates: {e}")

    # Fallback to skills matching if no job role
    if not skills:
        return err("Please provide either a job_role_id or skills to shortlist.")

    skills_list = [s.strip().lower() for s in skills.split(",")]
    
    matched = [
        {"id": c.id, "name": c.name}
        for c in candidates
        if any(skill in (",".join(c.skills or [])).lower() for skill in skills_list)
    ]
    matched = matched[:limit]

    msg = f"Shortlisted: {', '.join(c['name'] for c in matched) or 'none'}."
    return ok(msg, results=matched)
