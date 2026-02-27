from langchain_core.tools import tool
from django.utils.dateparse import parse_datetime
from django.utils import timezone
from core.models.recruitment import Candidate, Interview
from core.ai.agentic.tools.utils import ok, err, get_org, resolve_candidate_emails, resolve_natural_time
import logging

logger = logging.getLogger("harvey")

@tool("schedule_interview", return_direct=True)
def schedule_interview(candidate: str, start_time: str, job_title: str = "Candidate", duration_minutes: int = 30, user=None) -> str:
    """
    Schedules a candidate interview for the current user.
    ONLY pick this tool if the user explicitly uses the word 'interview'.
    For meetings, invites, or generic calendar events, use create_calendar_event_tool.
    candidate: The Name or Email of the candidate.
    start_time: Natural language time (e.g., 'monday 3pm', 'tomorrow at 10am').
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

    # 3. Resolve Time using Python
    from core.ai.agentic.tools.utils import get_user_timezone
    tz = get_user_timezone(user, org)

    dt = resolve_natural_time(start_time, user_tz=tz)
    if not dt:
        return err(f"I couldn't understand the interview time '{start_time}'. Please try something like 'monday 3pm'.")

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
            from core.ai.agentic.tools.utils import create_calendar_event_helper
            import datetime
            
            end_dt = dt + datetime.timedelta(minutes=duration_minutes)
            
            event_title = f"{job_title} Interview"
            attendees_list = [c_obj.email]
            if user.email:
                attendees_list.append(user.email)
            
            description = f"Interview for {job_title} role with {c_obj.name}."
            
            event_result, final_tz = create_calendar_event_helper(
                title=event_title,
                start_dt=dt,
                end_dt=end_dt,
                attendees_list=attendees_list,
                description=description,
                user=user,
                tz=tz
            )
            
            calendar_link = event_result.get('htmlLink', '')
        except Exception as cal_err:
            logger.error(f"Calendar Invite failed: {cal_err}")

        msg = f"I have confirmed that the {job_title} interview with {c_obj.name} is scheduled for {dt.strftime('%A, %B %d at %I:%M %p')}."
        if calendar_link:
            msg += f" Google Calendar Link: {calendar_link}"
        
        return ok(msg, interview_id=i.id, when=str(dt), link=calendar_link)
        
    except Exception as e:
        return err(f"Database Error: {str(e)}")


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
