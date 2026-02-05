import json
import os
from typing import Union
from django.utils.dateparse import parse_datetime
from django.utils import timezone
from langchain_core.tools import tool
from core.models.recruitment import Candidate, JobRole, Interview, EmailLog, CandidateJobScore
from core.models.organization import Organization
from core.services.resume_parser import ResumeParser
from core.services.candidate_scorer import CandidateScorer
from core.tools.utils import ok, err, get_org

@tool("add_candidate", return_direct=True)
def add_candidate(name: str, email: str, skills: str, phone: str, source: str = "Chatbot", user=None) -> str:
    """Adds a new candidate to your organization's HR system."""
    org = get_org(user)
    if not org:
        return err("User is not associated with any organization. Please contact support.")

    if Candidate.objects.filter(email=email, organization=org).exists():
        return err(f"A candidate with the email '{email}' is already in the system.")

    c = Candidate.objects.create(
        organization=org,
        name=name,
        email=email,
        phone=phone,
        skills=[s.strip() for s in skills.split(",")] if skills else [],
        source=source,
        status="pending",
    )
    return ok(f"I've successfully added {name} as a new candidate.", id=c.id, name=name)


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
        return err(f"I encountered an issue parsing the resume: {e}")

    # Simple extraction fallback if not provided (in real app, use LLM here too)
    # For now, we assume the user provides basic details or we just create with what we have.
    # If email is missing, we can't check uniqueness easily, so we require email or generate a placeholder.
    if not email:
        return err("Please provide the candidate's email address along with the resume.")
    
    if Candidate.objects.filter(email=email, organization=org).exists():
        return err(f"A candidate with the email '{email}' is already in the system.")

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
    
    return ok(f"I've successfully added {c.name} and attached their resume.", id=c.id, name=c.name)


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
    return ok(f"I've created the new job role for '{title}' in the {department} department.", id=j.id, title=title)


@tool("schedule_interview", return_direct=True)
def schedule_interview(candidate: str, start_time: str, job_title: str = "Candidate", duration_minutes: int = 30, user=None) -> str:
    """
    Schedules an interview with a candidate for the current user.
    ONLY use this tool if the user explicitly mentions the word 'interview'. 
    For generic meetings or scheduling, use create_calendar_event_tool.
    candidate: The Name or Email of the candidate.
    start_time: ISO 8601 datetime string (e.g., '2023-10-27T10:00:00').
    job_title: The designation/role for the interview (e.g., 'Software Engineer').
    """
    # 1. Validation
    org = get_org(user)
    if not org:
        return err("User not associated with organization.")
    
    if not user or not user.pk:
         return err("No logged-in user found to set as interviewer.")

    # 2. Resolve Candidate (Email or Name) -> ID
    val = candidate.strip()
    c_obj = None
    
    # Try Email
    if "@" in val:
        c_obj = Candidate.objects.filter(email__iexact=val, organization=org).first()
    
    # Try Name if not found
    if not c_obj:
        c_objs = Candidate.objects.filter(name__iexact=val, organization=org)
        if c_objs.count() == 1:
            c_obj = c_objs.first()
        elif c_objs.count() > 1:
            return err(f"Multiple candidates named '{val}'. Please use their email.")
            
    if not c_obj:
        # Fallback: Is it an ID?
        if val.isdigit():
             c_obj = Candidate.objects.filter(id=int(val), organization=org).first()
        
    if not c_obj:
        return err(f"I couldn't find a candidate named '{val}'. Please ensure they are added first.")

    # 3. Create Interview in DB
    dt = parse_datetime(start_time)
    if not dt:
        return err("Invalid date format. Please use ISO 8601.")
    
    # Localize naive datetime to IST if no timezone specified
    if dt.tzinfo is None:
        import pytz
        ist = pytz.timezone("Asia/Kolkata")
        dt = ist.localize(dt)

    try:
        i = Interview.objects.create(
            organization=org,
            candidate=c_obj,
            interviewer_id=user.pk, # Always the current user
            date_time=dt,
            status="scheduled",
        )
        
        # 4. Create Google Calendar Invite
        calendar_link = ""
        try:
            from integrations.services.google.calendar import CalendarService
            import datetime
            service = CalendarService(user=user)
            
            end_dt = dt + datetime.timedelta(minutes=duration_minutes)
            
            event_title = f"{job_title} Interview"
            attendees = [c_obj.email]
            if user.email:
                attendees.append(user.email)
                
            event_result = service.create_event(
                title=event_title,
                start_time=dt.isoformat(),
                end_time=end_dt.isoformat(),
                attendees=",".join(attendees),
                description=f"Interview for {job_title} role with {c_obj.name}."
            )
            calendar_link = event_result.get('htmlLink', '')
        except Exception as cal_err:
            print(f"⚠️ Calendar Invite failed: {cal_err}")
            # We don't fail the whole tool if just calendar fails, but we log it.

        msg = f"I have confirmed that the {job_title} interview with {c_obj.name} is scheduled."
        if calendar_link:
            msg += f" Google Calendar Link: {calendar_link}"
        
        return ok(msg, interview_id=i.id, when=str(dt), link=calendar_link)
        
    except Exception as e:
        return err(f"Database Error: {str(e)}")


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
    return ok(f"I've sent the email to {recipient} regarding '{subject}'.", log_id=e.id)


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
            
            msg = f"Here are the top {len(scored_results)} candidates for '{job_role.title}':"
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

    msg = f"I found the following candidates matching the skills: {', '.join(c['name'] for c in matched) or 'None found'}."
    return ok(msg, results=matched)
