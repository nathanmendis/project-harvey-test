from langchain_core.tools import tool
from django.utils.dateparse import parse_datetime
from django.utils import timezone
from core.models.recruitment import Candidate, Interview
from core.ai.agentic.tools.utils import ok, err, get_org, resolve_candidate_emails

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
