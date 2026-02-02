from langchain.tools import tool
import json

@tool
def create_calendar_event_tool(title: str, start_time: str, end_time: str, description: str = "", attendees: str = "", user=None) -> str:
    """
    Create a calendar event.
    Use this tool when the user asks to schedule a meeting or add an event to their calendar.
    'start_time' and 'end_time' should be in ISO format (e.g., '2023-10-27T10:00:00').
    'attendees' should be a comma-separated list of email addresses.
    """
    # Resolve service
    try:
        from integrations.services.google.calendar import CalendarService
        service = CalendarService(user=user)
        
        # Add the logged-in user to attendees if available (so they see it on their calendar too)
        attendee_list = []
        if attendees:
            attendee_list = [a.strip() for a in attendees.split(',') if a.strip()]
        
        # If user is requesting this, they probably want to be invited (since the bot is the organizer)
        if user and user.email and user.email not in attendee_list:
            attendee_list.append(user.email)
            
        final_attendees = ",".join(attendee_list)

        event_result = service.create_event(
            title=title,
            start_time=start_time,
            end_time=end_time,
            description=description,
            attendees=final_attendees
        )
        
        return json.dumps({
            "status": "success",
            "message": f"Event '{title}' created.",
            "link": event_result.get('htmlLink'),
            "details": {
                "title": title,
                "start": start_time,
                "end": end_time,
                "attendees": final_attendees
            }
        })
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"Failed to create event: {str(e)}"
        })
