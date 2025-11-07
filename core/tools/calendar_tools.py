# core/actions/calendar_tools.py
from datetime import datetime
from django.utils.timezone import make_aware
from ..models import CalendarEvent
from django.contrib.auth import get_user_model
from .base import ActionResult
User = get_user_model()

def create_calendar_event(payload, user):
    fields = payload.get("fields", {}) or {}
    org = getattr(user, "organization", None)
    title = fields.get("title")
    date_time = fields.get("date_time")
    link = fields.get("location_link", None)
    participants_ids = fields.get("participants", [])

    if not title or not date_time:
        return ActionResult(ok=False, message="⚠️ Missing title or date/time.")

    dt = make_aware(datetime.fromisoformat(date_time))
    event = CalendarEvent.objects.create(
        organization=org,
        title=title,
        date_time=dt,
        location_link=link,
    )

    if participants_ids:
        participants = User.objects.filter(id__in=participants_ids)
        event.participants.set(participants)

    return ActionResult(ok=True, message=f"🗓 Event '{title}' scheduled for {dt.strftime('%b %d, %Y %H:%M')}.")
