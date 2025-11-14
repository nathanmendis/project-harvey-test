import re, difflib, dateparser
from datetime import datetime
from django.utils.timezone import get_current_timezone

from .base_normalizers import fix_typos, normalize_ordinals, extract_duration
from .fuzzy_months import fuzzy_fix_months

def extract_event_fields(text: str, existing_context=None):
    existing_context = existing_context or {}

    cleaned = fuzzy_fix_months(normalize_ordinals(fix_typos(text)))

    parsed_dt = dateparser.parse(
        cleaned,
        settings={
            "PREFER_DATES_FROM": "future",
            "TIMEZONE": str(get_current_timezone()),
            "RETURN_AS_TIMEZONE_AWARE": True,
        },
    )

    # If missing time or date, try merging with context
    if not parsed_dt:
        prev = existing_context.get("date_time")
        if prev:
            prev_dt = dateparser.parse(prev, settings={"RETURN_AS_TIMEZONE_AWARE": True})
            time_match = re.search(r'\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b', cleaned)
            if prev_dt and time_match:
                hour = int(time_match.group(1))
                minute = int(time_match.group(2) or 0)
                ampm = (time_match.group(3) or "").lower()
                if ampm == "pm" and hour < 12: hour += 12
                if ampm == "am" and hour == 12: hour = 0
                parsed_dt = datetime(
                    prev_dt.year, prev_dt.month, prev_dt.day,
                    hour, minute, tzinfo=get_current_timezone()
                )

    duration = extract_duration(cleaned) or existing_context.get("duration_minutes")
    participants = re.findall(r"with\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)", text)
    if not participants:
        participants = existing_context.get("participants", [])

    title = None
    t1 = re.search(r"about\s+([A-Za-z0-9\s]+)", text)
    if t1:
        title = t1.group(1).strip().capitalize()
    elif participants:
        title = f"Meeting with {', '.join(participants)}"
    else:
        title = existing_context.get("title")

    result = {
        "title": title,
        "date_time": parsed_dt.isoformat() if parsed_dt else existing_context.get("date_time"),
        "participants": participants,
        "duration_minutes": duration,
    }

    print("🧩 EVENT DEBUG:", result)
    return {k: v for k, v in result.items() if v is not None}
