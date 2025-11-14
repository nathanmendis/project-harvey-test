import re, dateparser
from datetime import datetime, timedelta
from django.utils.timezone import get_current_timezone, localtime

from .base_normalizers import fix_typos, normalize_ordinals, extract_duration
from .fuzzy_months import fuzzy_fix_months

def extract_interview_fields(text: str, existing_context=None):
    existing_context = existing_context or {}
    raw = text or ""

    cleaned = fuzzy_fix_months(normalize_ordinals(fix_typos(raw)))

    # 1. Candidate ID
    cid = None
    m = re.search(r"candidate\s*(?:id)?\s*(?:is|:)?\s*(\d+)\b", cleaned)
    if m:
        cid = m.group(1)
    elif existing_context.get("candidate_id"):
        cid = str(existing_context["candidate_id"])

    # 2. Duration
    duration = extract_duration(cleaned) or existing_context.get("duration_minutes")

    # 3. Time
    time_match = re.search(r'\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b', cleaned)
    time_str = None
    if time_match:
        hour, minute = int(time_match.group(1)), int(time_match.group(2) or 0)
        ampm = (time_match.group(3) or "").lower()
        if ampm == "pm" and hour < 12: hour += 12
        if ampm == "am" and hour == 12: hour = 0
        time_str = f"{hour:02d}:{minute:02d}"

    # 4. Date detection
    tz = get_current_timezone()
    now = datetime.now(tz)
    parsed_dt = None

    if "tomorrow" in cleaned:
        date = now + timedelta(days=1)
        parsed_dt = datetime.combine(date.date(), datetime.strptime(time_str or "10:00", "%H:%M").time(), tz)

    # fallback: full date
    if not parsed_dt:
        parsed_dt = dateparser.parse(
            cleaned,
            settings={
                "TIMEZONE": str(tz),
                "RETURN_AS_TIMEZONE_AWARE": True,
                "PREFER_DATES_FROM": "future",
            },
        )

    if not parsed_dt and existing_context.get("when"):
        parsed_dt = dateparser.parse(existing_context["when"], settings={"RETURN_AS_TIMEZONE_AWARE": True})

    if parsed_dt:
        parsed_dt = localtime(parsed_dt)

    result = {}
    if cid: result["candidate_id"] = cid
    if parsed_dt: result["when"] = parsed_dt.isoformat()
    if duration: result["duration_minutes"] = duration

    print("🧩 INTERVIEW DEBUG:", {"raw": raw, "cleaned": cleaned, **result})
    return result
