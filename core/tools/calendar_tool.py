from langchain.tools import tool
import json

@tool
def create_calendar_event_tool(title: str, start_time: str, end_time: str, description: str = "", attendees: str = "") -> str:
    """
    Create a calendar event.
    Use this tool when the user asks to schedule a meeting or add an event to their calendar.
    'start_time' and 'end_time' should be in ISO format (e.g., '2023-10-27T10:00:00').
    'attendees' should be a comma-separated list of email addresses.
    """
    # Placeholder: In the future, this will resolve the user's preferred provider
    # and use the appropriate CalendarService (Google/Microsoft).
    
    return json.dumps({
        "status": "success",
        "message": f"Event '{title}' created.",
        "details": {
            "title": title,
            "start": start_time,
            "end": end_time,
            "attendees": attendees
        }
    })
