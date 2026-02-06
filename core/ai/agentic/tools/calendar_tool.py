from langchain.tools import tool
import json
from .utils import ok, err, get_org, resolve_user_emails

@tool
def create_calendar_event_tool(title: str, start_time: str, end_time: str, description: str = "", attendees: str = "", user=None) -> str:
    """
    Create a calendar event.
    Use this tool for all generic meeting scheduling, appointments, or when the user says "schedule" or "meeting" 
    WITHOUT explicitly using the word "interview".
    'start_time' and 'end_time' should be in ISO format (e.g., '2023-10-27T10:00:00').
    'attendees' should be a comma-separated list of email addresses or names.
    """
    org = get_org(user)
    
    # Resolve service
    try:
        from integrations.google.calendar import CalendarService
        service = CalendarService(user=user)
        
        attendee_list = []
        if attendees:
            raw_attendees = [a.strip() for a in attendees.split(',') if a.strip()]
            for raw_a in raw_attendees:
                if "@" in raw_a:
                    attendee_list.append(raw_a)
                elif org:
                    # Try resolving as user name
                    emails = resolve_user_emails(raw_a, org)
                    if emails:
                        attendee_list.extend(emails)
                    else:
                        # If not resolved, keep as is (maybe it's an email without @? unlikely but safer)
                        attendee_list.append(raw_a)
                else:
                    attendee_list.append(raw_a)
        
        # If user is requesting this, they probably want to be invited (since the bot is the organizer)
        if user and user.email and user.email not in attendee_list:
            attendee_list.append(user.email)
            
        final_attendees = ",".join(list(set(attendee_list)))

        event_result = service.create_event(
            title=title,
            start_time=start_time,
            end_time=end_time,
            description=description,
            attendees=final_attendees
        )
        
        link = event_result.get('htmlLink')
        message = f"I have successfully scheduled the event '{title}' on your calendar."
        if link:
            message += f" Link: {link}"
        
        return ok(message, link=link, title=title, start=start_time, end=end_time, attendees=final_attendees)

    except Exception as e:
        return err(f"Failed to create event: {str(e)}")
