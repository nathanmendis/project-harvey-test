import re
import dateparser
from datetime import datetime ,timedelta
from django.utils.timezone import get_current_timezone
# add at top of file
import difflib

# --- helper: fuzzy-normalize month-like tokens ---
MONTHS = [
    "january", "february", "march", "april", "may", "june",
    "july", "august", "september", "october", "november", "december"
]
MONTH_ABB = {m[:3]: m for m in MONTHS}

def _fuzzy_fix_months(text: str) -> str:
    """
    Turn tokens that look like month fragments into a canonical month name.
    Examples:
      '13NOv' -> '13 november'
      '13 novv' -> '13 november'
      '13 N0v' -> '13 november'
    """
    # separate digits from letters so '13NOv' -> '13 NOv'
    t = re.sub(r'(\d)([A-Za-z])', r'\1 \2', text)
    t = re.sub(r'([A-Za-z])(\d)', r'\1 \2', t)

    tokens = t.split()
    fixed_tokens = []
    for tok in tokens:
        # remove stray non-alpha from token for month guessing, e.g. 'N0v' -> 'Nv'
        cleaned = re.sub(r'[^A-Za-z]', '', tok).lower()
        if not cleaned:
            fixed_tokens.append(tok)
            continue

        # if token length 3-6 and resembles a month, attempt fuzzy match
        if 2 <= len(cleaned) <= 6:
            # try direct abb map
            abb = cleaned[:3]
            if abb in MONTH_ABB:
                fixed_tokens.append(MONTH_ABB[abb])
                continue
            # fuzzy match against month names
            match = difflib.get_close_matches(cleaned, MONTHS, n=1, cutoff=0.6)
            if match:
                fixed_tokens.append(match[0])
                continue

        fixed_tokens.append(tok)

    return " ".join(fixed_tokens)
# ---------------- COMMON NORMALIZERS ---------------- #
MISSPELLINGS = {
    "tomorow": "tomorrow",
    "tomorro": "tomorrow",
    "novemeber": "november",
}

def _fix_common_typos(text: str) -> str:
    """Fixes common spelling mistakes like 'tomorow' → 'tomorrow'."""
    lowered = text.lower()
    for bad, good in MISSPELLINGS.items():
        lowered = lowered.replace(bad, good)
    return lowered

def _normalize_ordinals(text: str) -> str:
    """Normalizes '13th November' → '13 November' for easier parsing."""
    return re.sub(r'(\d+)(st|nd|rd|th)\b', r'\1', text, flags=re.IGNORECASE)

def _extract_duration_minutes(text: str):
    """Extracts meeting duration like '1 hour' → 60, '30 mins' → 30."""
    m = re.search(r"(\d+)\s*(hours|hour|hrs|hr|minutes|minute|mins|min)\b", text, re.IGNORECASE)
    if not m:
        return None
    val = int(m.group(1))
    unit = m.group(2).lower()
    return val * 60 if "hour" in unit or "hr" in unit else val


# ---------------- EMAIL EXTRACTION ---------------- #
def extract_email(text: str):
    """Extracts the first email address found in text."""
    m = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", text)
    return m.group(0) if m else None


def extract_email_fields(text: str):
    """Extracts recipient, subject, and body fields for emails."""
    recipient = extract_email(text)
    subject = "Message"
    body = text.strip() if not recipient else None
    res = {}
    if recipient:
        res["recipient"] = recipient
    if body:
        res["body"] = body
    res["subject"] = subject
    return res


# ---------------- CANDIDATE EXTRACTION ---------------- #
def extract_candidate_fields(text: str):
    """Extracts candidate details like name, email, phone, and role."""
    name = re.search(r"(?:name is|named)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)", text, re.IGNORECASE)
    email = extract_email(text)
    phone = re.search(r"\b\d{8,15}\b", text)
    role = re.search(r"(?:role|position)\s*(?:is|:)?\s*([A-Za-z ]+)", text)
    return {
        "name": name.group(1) if name else None,
        "email": email,
        "phone": phone.group(0) if phone else None,
        "role": role.group(1).strip() if role else None,
    }


# ---------------- INTERVIEW EXTRACTION ---------------- #

def extract_interview_fields(text: str, existing_context: dict = None):
    """
    Final robust extractor for scheduling interviews.
    Parses things like:
    - "candidate id is 2 and it will be tomorow 12th nov 1pm for an hour"
    - "schedule interview with candidate 5 next monday 10am for 45 minutes"
    """
    existing_context = existing_context or {}
    raw = text or ""
    cleaned = _fix_common_typos(raw).replace("tomorroww", "tomorrow")
    cleaned = _normalize_ordinals(cleaned)
    cleaned = _fuzzy_fix_months(cleaned)

    # --- candidate id ---
    cid = None
    m = re.search(r"candidate\s*(?:id)?\s*(?:is|:)?\s*(\d+)\b", cleaned, re.IGNORECASE)
    if m:
        cid = m.group(1)
    elif existing_context.get("candidate_id"):
        cid = str(existing_context.get("candidate_id"))

    # --- duration ---
    duration = None
    md = re.search(r'(\d+)\s*(hour|hours|hr|hrs|minutes|min|mins)\b', cleaned, re.IGNORECASE)
    if md:
        val, unit = int(md.group(1)), md.group(2).lower()
        duration = val * 60 if "hour" in unit or "hr" in unit else val
    if not duration and existing_context.get("duration_minutes"):
        duration = existing_context["duration_minutes"]

    # --- time component ---
    time_match = re.search(r'\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b', cleaned, re.IGNORECASE)
    time_str = None
    if time_match:
        hour = int(time_match.group(1))
        minute = int(time_match.group(2) or 0)
        ampm = (time_match.group(3) or "").lower()
        if ampm == "pm" and hour < 12:
            hour += 12
        if ampm == "am" and hour == 12:
            hour = 0
        time_str = f"{hour:02d}:{minute:02d}"

    # --- detect relative / absolute day ---
    parsed_dt = None
    tz = get_current_timezone()
    now = datetime.now(tz)

    if "tomorrow" in cleaned:
        base_date = (now + timedelta(days=1)).date()
        if time_str:
            parsed_dt = datetime.combine(base_date, datetime.strptime(time_str, "%H:%M").time(), tz)
        else:
            parsed_dt = datetime.combine(base_date, datetime.strptime("10:00", "%H:%M").time(), tz)

    elif "next" in cleaned:
        # crude detection for 'next monday'
        days = ["monday","tuesday","wednesday","thursday","friday","saturday","sunday"]
        for i, d in enumerate(days):
            if d in cleaned:
                today_idx = now.weekday()
                target = (i - today_idx + 7) % 7
                if target == 0: target = 7
                base_date = (now + timedelta(days=target)).date()
                parsed_dt = datetime.combine(base_date, datetime.strptime(time_str or "10:00","%H:%M").time(), tz)
                break

    if not parsed_dt:
        # absolute e.g. "12 nov 1pm"
        dm = re.search(r'(\d{1,2}(?:st|nd|rd|th)?\s+[A-Za-z]{3,9})', cleaned)
        phrase = dm.group(1) if dm else ""
        if time_str:
            phrase = f"{phrase} {time_str}"
        if phrase:
            parsed_dt = dateparser.parse(
                phrase,
                languages=["en"],
                settings={
                    "DATE_ORDER": "DMY",
                    "TIMEZONE": str(tz),
                    "RETURN_AS_TIMEZONE_AWARE": True,
                    "PREFER_DATES_FROM": "future",
                    "RELATIVE_BASE": now,
                },
            )

    # fallback: use existing when
    if not parsed_dt and existing_context.get("when"):
        try:
            parsed_dt = dateparser.parse(existing_context["when"], settings={"RETURN_AS_TIMEZONE_AWARE": True})
        except Exception:
            parsed_dt = None
    if parsed_dt:
        from django.utils.timezone import localtime
        parsed_dt = localtime(parsed_dt)

    result = {}
    if cid:
        result["candidate_id"] = cid
    if parsed_dt:
        result["when"] = parsed_dt.isoformat()
    if duration:
        result["duration_minutes"] = duration

    print("🧩 DEBUG extract_interview_fields ->", {"raw": raw, "cleaned": cleaned, **result})
    return result
# ---------------- EVENT / MEETING EXTRACTION ---------------- #
def extract_event_fields(text: str, existing_context: dict = None):
    """
    Robust extractor: normalizes typos & fuzzy-months, merges partial date/time fragments,
    and returns title, date_time (ISO), participants, duration_minutes.
    """
    existing_context = existing_context or {}

    # 1) basic cleanup + typo fixes + ordinals
    cleaned = _fix_common_typos(text)
    cleaned = _normalize_ordinals(cleaned)

    # 2) fuzzy-fix month-like tokens (handles '13NOv', '13 novv', etc.)
    cleaned = _fuzzy_fix_months(cleaned)

    # 3) First attempt: parse entire cleaned string
    parsed_dt = dateparser.parse(
        cleaned,
        settings={
            "PREFER_DATES_FROM": "future",
            "TIMEZONE": str(get_current_timezone()),
            "RETURN_AS_TIMEZONE_AWARE": True,
        },
    )

    # 4) If parse failed, try merging with existing_context (time-only or date-only fragments)
    if not parsed_dt:
        prev_dt = None
        prev_raw = existing_context.get("date_time")
        if prev_raw:
            try:
                prev_dt = dateparser.parse(prev_raw, settings={"RETURN_AS_TIMEZONE_AWARE": True})
            except Exception:
                prev_dt = None

        # detect a time fragment like "at 10am" or "10:30 am"
        time_match = re.search(r'\b(at\s*)?(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b', cleaned, re.IGNORECASE)
        if prev_dt and time_match:
            # combine date from prev_dt and time from new fragment
            hour = int(time_match.group(2))
            minute = int(time_match.group(3) or 0)
            ampm = (time_match.group(4) or "").lower()
            if ampm == "pm" and hour < 12:
                hour += 12
            if ampm == "am" and hour == 12:
                hour = 0
            try:
                parsed_dt = datetime(
                    prev_dt.year, prev_dt.month, prev_dt.day,
                    hour, minute, tzinfo=get_current_timezone()
                )
            except Exception:
                parsed_dt = None
        else:
            # if text contains 'tomorrow' or 'today' without a time, parse it (dateparser often handles this)
            if "tomorrow" in cleaned or "today" in cleaned:
                parsed_dt = dateparser.parse(cleaned, settings={
                    "PREFER_DATES_FROM": "future",
                    "TIMEZONE": str(get_current_timezone()),
                    "RETURN_AS_TIMEZONE_AWARE": True,
                })

            # as last resort: try extracting explicit day + month via regex (e.g., "13 nov")
            if not parsed_dt:
                m = re.search(r'\b(\d{1,2})\s+([A-Za-z]{3,})\b', cleaned)
                if m:
                    day = int(m.group(1))
                    mon_token = m.group(2).lower()
                    # fuzzy match month token
                    match = difflib.get_close_matches(mon_token, MONTHS, n=1, cutoff=0.5)
                    if match:
                        mon = MONTHS.index(match[0]) + 1
                        # try to use this month in the current year or next if past
                        now = datetime.now(get_current_timezone())
                        year = now.year
                        try:
                            parsed_dt = dateparser.parse(f"{day} {match[0]} {year}", settings={
                                "TIMEZONE": str(get_current_timezone()),
                                "RETURN_AS_TIMEZONE_AWARE": True,
                                "PREFER_DATES_FROM": "future"
                            })
                            # if parsing produced a past date, try next year
                            if parsed_dt and parsed_dt < now:
                                parsed_dt = dateparser.parse(f"{day} {match[0]} {year+1}", settings={
                                    "TIMEZONE": str(get_current_timezone()),
                                    "RETURN_AS_TIMEZONE_AWARE": True,
                                    "PREFER_DATES_FROM": "future"
                                })
                        except Exception:
                            parsed_dt = None

    # 5) Duration
    duration = _extract_duration_minutes(cleaned) or existing_context.get("duration_minutes")

    # 6) Participants (greedy 'with X' capture)
    participants = re.findall(r"with\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)", text)
    participants = [p.strip() for p in participants if p]
    if not participants and "participants" in existing_context:
        participants = existing_context["participants"]

    # 7) Title / topic
    title = None
    about = re.search(r"about\s+([A-Za-z0-9\s]+)", text, re.IGNORECASE)
    if about:
        title = about.group(1).strip().capitalize()
    elif participants:
        title = f"Meeting with {', '.join(participants)}"
    elif existing_context.get("title"):
        title = existing_context["title"]

    # 8) Build result
    result = {
        "title": title,
        "date_time": parsed_dt.isoformat() if parsed_dt else existing_context.get("date_time"),
        "participants": participants,
        "duration_minutes": duration,
    }

    # debug print (remove in production)
    print("🧩 DEBUG extract_event_fields (robust):", result)
    return {k: v for k, v in result.items() if v is not None}