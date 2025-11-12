# core/actions/calendar_tools.py
from datetime import datetime
from django.utils.timezone import make_aware, get_current_timezone
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from ..models import CalendarEvent
from .base import ActionResult
import dateparser

User = get_user_model()


def create_calendar_event(payload, user):
    """
    Creates a calendar event for the user's organization.
    Supports both ISO and natural date strings (e.g., '13 November 2025 10 AM').
    """
    org = getattr(user, "organization", None)
    if org is None:
        return ActionResult(ok=False, message="⚠️ User is not linked to any organization.")

    fields = payload.get("fields", {}) or {}
    title = (fields.get("title") or "").strip()
    date_time_raw = (fields.get("date_time") or "").strip()
    link = fields.get("location_link") or None
    participants_ids = fields.get("participants", [])
    duration_minutes = fields.get("duration_minutes")

    # --- Validation ---
    if not title:
        return ActionResult(ok=False, message="⚠️ Missing event title.")
    if not date_time_raw:
        return ActionResult(ok=False, message="⚠️ Missing event date/time.")

    # --- Parse datetime (support ISO + natural language) ---
    dt = None
    try:
        dt = datetime.fromisoformat(date_time_raw)
        if dt.tzinfo is None:
            dt = make_aware(dt, timezone=get_current_timezone())
    except Exception:
        parsed = dateparser.parse(
            date_time_raw,
            settings={"TIMEZONE": "Asia/Kolkata", "RETURN_AS_TIMEZONE_AWARE": True},
        )
        if parsed:
            dt = parsed
    if not dt:
        return ActionResult(ok=False, message=f"⚠️ Unable to parse date/time: '{date_time_raw}'.")

    # --- Prevent duplicates (optional safeguard) ---
    if CalendarEvent.objects.filter(organization=org, title=title, date_time=dt).exists():
        return ActionResult(ok=True, message=f"ℹ️ Event '{title}' already scheduled at {dt.strftime('%b %d, %Y %I:%M %p')}.")

    # --- Create event ---
    try:
        event = CalendarEvent.objects.create(
            organization=org,
            title=title,
            date_time=dt,
            location_link=link,
            duration_minutes=duration_minutes or 60,  # default to 1 hour
        )

        # --- Attach participants if provided ---
        if participants_ids:
            if isinstance(participants_ids, list) and all(isinstance(x, int) for x in participants_ids):
                participants = User.objects.filter(id__in=participants_ids)
                event.participants.set(participants)
            else:
                # Optional: attempt matching by email/name
                matches = User.objects.filter(email__in=participants_ids)
                if matches.exists():
                    event.participants.set(matches)

        msg_time = dt.strftime("%b %d, %Y %I:%M %p")
        return ActionResult(ok=True, message=f"🗓 Event '{title}' scheduled for {msg_time}.")

    except IntegrityError as e:
        return ActionResult(ok=False, message=f"⚠️ Database error while scheduling event: {e}")
    except Exception as e:
        return ActionResult(ok=False, message=f"⚠️ Unexpected error: {e}")
