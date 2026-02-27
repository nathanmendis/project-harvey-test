
from langchain.tools import tool
import json
import logging
import dateparser
import datetime
import pytz
from django.utils import timezone
from .utils import ok, err, get_org, resolve_user_emails, resolve_natural_time

logger = logging.getLogger("harvey")


@tool
def create_calendar_event_tool(
    title: str,
    start_time: str,
    end_time: str = None,
    description: str = "",
    attendees: str = "",
    user=None,
) -> str:
    """
    Create a calendar event.
    Use this for generic meeting scheduling.
    """
    from integrations.google.calendar import CalendarService
    from .utils import get_user_timezone, create_calendar_event_helper
    
    org = get_org(user)

    # 1. Fetch user's actual calendar timezone FIRST (Production safe)
    tz = get_user_timezone(user, org)

    # 2. Resolve Times using the correct TZ
    try:
        start_dt = resolve_natural_time(start_time, tz)
        if not start_dt:
            return err(f"I couldn't understand the start time '{start_time}'. Please try something like 'monday 3pm'.")

        if end_time:
            end_dt = resolve_natural_time(end_time, tz)
            if not end_dt:
                end_dt = start_dt + datetime.timedelta(hours=1)
        else:
            end_dt = start_dt + datetime.timedelta(hours=1)

    except Exception as parse_e:
        logger.error(f"Time parsing error: {str(parse_e)}")
        return err(f"Time parsing error: {str(parse_e)}")

    # 3. Resolve Attendees
    attendee_list = []
    try:
        if attendees:
            raw_attendees = [a.strip() for a in attendees.split(",") if a.strip()]
            for raw_a in raw_attendees:
                if "@" in raw_a:
                    attendee_list.append(raw_a)
                elif org:
                    emails = resolve_user_emails(raw_a, org)
                    if emails:
                        attendee_list.extend(emails)

        if user and user.email:
            attendee_list.append(user.email)
        attendee_list = list(set(attendee_list))
    except Exception as e:
        logger.error(f"Attendee resolution failed: {str(e)}")

    # 4. Create Event via Helper
    try:
        event_result, final_tz = create_calendar_event_helper(
            title=title,
            start_dt=start_dt,
            end_dt=end_dt,
            attendees_list=attendee_list,
            description=description,
            user=user,
            tz=tz
        )

        link = event_result.get("htmlLink")
        message = (
            f"I have successfully scheduled the event '{title}' "
            f"on your calendar for {start_dt.strftime('%A, %B %d at %I:%M %p')}."
        )
        if link:
            message += f" Link: {link}"

        return ok(
            message,
            link=link,
            title=title,
            start=start_dt.isoformat(),
            end=end_dt.isoformat(),
            timezone=final_tz,
            attendees=",".join(attendee_list),
        )

    except Exception as e:
        logger.error(f"Failed to create event: {str(e)}")
        return err(f"Failed to create event: {str(e)}")