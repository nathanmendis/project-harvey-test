import json
import os
from typing import Union
from django.utils.dateparse import parse_datetime
from django.utils import timezone
from django.db.models import Q
from langchain_core.tools import tool
from core.models.recruitment import Candidate, JobRole, Interview, EmailLog, CandidateJobScore, LeaveRequest
from core.models.organization import Organization
from core.ai.utils.resume_parser import ResumeParser
from core.ai.utils.candidate_scorer import CandidateScorer
from .utils import ok, err, get_org, resolve_candidate_emails, is_valid_email

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

    # 2. Resolve Candidate (Email or Name) -> Email
    emails = resolve_candidate_emails(candidate, org)

    if not emails:
        return err(f"I couldn't find a candidate matching '{candidate}'. Please ensure they are added first.")

    if len(emails) > 1:
        return err(f"Multiple candidates found matching '{candidate}': {', '.join(emails)}. Please use their exact email.")

    resolved_email = emails[0]
    c_obj = Candidate.objects.filter(email=resolved_email, organization=org).first()

    if not c_obj:
        return err(f"Candidate with email '{resolved_email}' not found.")

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
            from integrations.google.calendar import CalendarService
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

    # 🔍 Resolve recipient
    emails = resolve_candidate_emails(recipient, org)
    
    if not emails:
        return err(f"Could not resolve recipient '{recipient}' to a valid candidate email.")

    if len(emails) > 1:
        return err(f"Multiple candidates found matching '{recipient}': {', '.join(emails)}. Please be more specific.")

    resolved_email = emails[0]

    e = EmailLog.objects.create(
        organization=org,
        recipient_email=resolved_email,
        subject=subject,
        body=body,
        status="sent",
        sent_time=timezone.now(),
    )
    return ok(f"I've sent the email to {resolved_email} regarding '{subject}'.", log_id=e.id)


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


@tool("list_candidates", return_direct=True)
def list_candidates(name: str = "", email: str = "", status: str = "", limit: int = 10, user=None) -> str:
    """
    Lists candidates with optional filters.
    Use this to search for candidates or see who has applied.
    """
    org = get_org(user)
    if not org:
        return err("User is not associated with any organization.")

    candidates = Candidate.objects.filter(organization=org)

    if name:
        candidates = candidates.filter(name__icontains=name)
    if email:
        candidates = candidates.filter(email__icontains=email)
    if status:
        candidates = candidates.filter(status__iexact=status)

    count = candidates.count()
    candidates = candidates.order_by("-created_at")[:limit]

    if count == 0:
        return ok("No candidates found matching your criteria.")

    # NLP-friendly output
    lines = [f"I found {count} candidate(s) (showing top {len(candidates)}):"]
    results = []
    
    for c in candidates:
        line = f"• {c.name} ({c.email}) - {c.status}"
        lines.append(line)
        results.append({"id": c.id, "name": c.name, "email": c.email, "status": c.status})

    return ok("\n".join(lines), results=results)


@tool("get_candidate_detail", return_direct=True)
def get_candidate_detail(candidate_id: int = None, email: str = None, user=None) -> str:
    """
    Retrieves detailed information about a specific candidate.
    Provide either candidate_id OR email.
    """
    org = get_org(user)
    if not org:
        return err("User is not associated with any organization.")

    c = None
    if candidate_id:
        c = Candidate.objects.filter(organization=org, id=candidate_id).first()
    elif email:
        c = Candidate.objects.filter(organization=org, email=email).first()

    if not c:
        return err("Candidate not found.")

    # Construct detail string
    skills_str = ", ".join(c.skills) if c.skills else "None listed"
    
    detail = [
        f"Candidate Profile: {c.name}",
        f" Email: {c.email}",
        f" Phone: {c.phone or 'N/A'}",
        f" Status: {c.status}",
        f" Skills: {skills_str}",
        f" Source: {c.source}",
    ]

    # Check for scores/applications
    scores = CandidateJobScore.objects.filter(candidate=c)
    if scores.exists():
        detail.append("\n**Job Applications & Scores:**")
        for s in scores:
            detail.append(f"- {s.job_role.title}: Score {s.score}/100")
            if s.justification:
                # Truncate justification if too long
                just = s.justification[:100] + "..." if len(s.justification) > 100 else s.justification
                detail.append(f"  *Insight: {just}*")

    return ok("\n".join(detail), id=c.id, name=c.name, email=c.email, full_data=str(c.__dict__))


@tool("list_job_roles", return_direct=True)
def list_job_roles(department: str = "", title: str = "", user=None) -> str:
    """Lists available job roles/openings."""
    org = get_org(user)
    if not org:
        return err("User not in organization.")

    jobs = JobRole.objects.filter(organization=org)
    
    if department:
        jobs = jobs.filter(department__icontains=department)
    if title:
        jobs = jobs.filter(title__icontains=title)

    if not jobs.exists():
        return ok("No job roles found.")

    results = []
    lines = [f"Here are the job roles for {org.name}:"]
    
    for j in jobs:
        lines.append(f"• **{j.title}** ({j.department})")
        results.append({"id": j.id, "title": j.title, "department": j.department})

    return ok("\n".join(lines), results=results)


@tool("get_job_role_detail", return_direct=True)
def get_job_role_detail(job_id: int, user=None) -> str:
    """Gets details for a specific job role."""
    org = get_org(user)
    if not org:
        return err("User not in organization.")

    j = JobRole.objects.filter(organization=org, id=job_id).first()
    if not j:
        return err(f"Job role with ID {job_id} not found.")

    detail = [
        f"Job Role: {j.title}",
        f"Department: {j.department}",
        f"Description:\n{j.description}",
        f"Requirements:\n{j.requirements}"
    ]

    return ok("\n".join(detail), id=j.id, title=j.title)


@tool("list_interviews", return_direct=True)
def list_interviews(candidate_name: str = "", limit: int = 5, user=None) -> str:
    """
    Lists upcoming interviews.
    """
    org = get_org(user)
    if not org:
        return err("User error.")
    
    interviews = Interview.objects.filter(organization=org).select_related('candidate')
    
    if candidate_name:
        interviews = interviews.filter(candidate__name__icontains=candidate_name)

    # Show upcoming first
    interviews = interviews.filter(date_time__gte=timezone.now()).order_by('date_time')[:limit]

    if not interviews.exists():
        return ok("No upcoming interviews found.")

    lines = ["**Upcoming Interviews:**"]
    results = []
    
    for i in interviews:
        local_time = timezone.localtime(i.date_time).strftime("%d %b %Y, %I:%M %p")
        lines.append(f"• {local_time}: **{i.candidate.name}** (Status: {i.status})")
        results.append({"id": i.id, "candidate": i.candidate.name, "time": str(i.date_time)})

    return ok("\n".join(lines), results=results)


@tool("list_leave_requests", return_direct=True)
def list_leave_requests(status: str = "pending", user=None) -> str:
    """
    Lists leave requests. Default shows pending requests.
    status options: 'pending', 'approved', 'rejected', 'all'.
    """
    org = get_org(user)
    if not org:
        return err("User error.")

    leaves = LeaveRequest.objects.filter(organization=org)
    
    if status != 'all':
        leaves = leaves.filter(status__iexact=status)
        
    leaves = leaves.order_by('-start_date')

    if not leaves.exists():
        return ok(f"No {status} leave requests found.")

    lines = [f"Found {leaves.count()} {status} leave request(s):"]
    results = []
    
    for l in leaves:
        duration = (l.end_date - l.start_date).days + 1
        lines.append(f"• **{l.employee.name}**: {l.leave_type} for {duration} day(s) ({l.start_date} to {l.end_date}) - {l.reason}")
        results.append({"id": l.id, "employee": l.employee.name, "status": l.status})

    return ok("\n".join(lines), results=results)
