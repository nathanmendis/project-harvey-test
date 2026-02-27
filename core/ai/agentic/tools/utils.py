import json
import re
import dateparser
import pytz
from django.utils import timezone
from django.db.models import Q
from django.contrib.auth import get_user_model

User = get_user_model()
EMAIL_REGEX = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"

def resolve_natural_time(time_str, user_tz="Asia/Kolkata", prefer_future=True):
    """
    Resolve natural language time string into timezone-aware datetime.
    """
    tz_obj = pytz.timezone(user_tz)
    now = timezone.now().astimezone(tz_obj)

    settings = {
        "RELATIVE_BASE": now.replace(tzinfo=None),
        "TIMEZONE": user_tz,
        "RETURN_AS_TIMEZONE_AWARE": False,
        "PREFER_DATES_FROM": "future" if prefer_future else "current",
    }

    dt = dateparser.parse(time_str, settings=settings)

    if dt:
        return tz_obj.localize(dt)

    return None



def ok(message, **data):
    return json.dumps({"ok": True, "message": message, **data})

def err(message):
    return json.dumps({"ok": False, "message": message})

def get_org(user):
    """Helper to get organization from user."""
    if user and getattr(user, "organization", None):
        return user.organization
    return None

def is_valid_email(value: str) -> bool:
    return bool(re.match(EMAIL_REGEX, value))

def resolve_entities(query: str, organization, model_class, search_fields: list):
    """
    Generic entity resolver within an organization.
    Returns a queryset of matches.
    """
    if not query:
        return model_class.objects.none()

    query = query.strip()
    
    # 1. Check if it's a valid email (if applicable to this model)
    if is_valid_email(query) and hasattr(model_class, 'email'):
        return model_class.objects.filter(organization=organization, email__iexact=query)

    # 2. Search by provided fields
    q_objects = Q()
    for field in search_fields:
        q_objects |= Q(**{f"{field}__icontains": query})
    
    return model_class.objects.filter(organization=organization).filter(q_objects)

def resolve_user_emails(query: str, organization):
    """Resolves a query to a list of User emails."""
    if is_valid_email(query):
        return [query.strip()]
    qs = resolve_entities(query, organization, User, ["username", "name"])
    return list(qs.values_list("email", flat=True).distinct())

def resolve_candidate_emails(query: str, organization):
    """Resolves a query to a list of Candidate emails."""
    if is_valid_email(query):
        return [query.strip()]
    from core.models.recruitment import Candidate
    qs = resolve_entities(query, organization, Candidate, ["name", "email"])
    return list(qs.values_list("email", flat=True).distinct())

def get_email_signature(user):
    """Generates a professional email signature for the user."""
    lines = ["Regards,"]

    name = (
        getattr(user, "name", None)
        or getattr(user, "get_full_name", lambda: None)()
        or getattr(user, "username", None)
        or "Team"
    )
    lines.append(name)

    role_map = {
        "employee": "Employee",
        "manager": "Manager",
        "hr": "HR Team",
        "org_admin": "Organization Admin",
    }
    role = role_map.get(getattr(user, "role", None))
    if role:
        lines.append(role)

    organization = getattr(user, "organization", None)
    if organization and getattr(organization, "name", None):
        lines.append(organization.name)

    email = getattr(user, "email", None)
    if email:
        lines.append(f"Email: {email}")

    return "\n".join(lines)

def send_email_helper(recipient_email, subject, body, user):
    """
    Centralized helper to send emails via Gmail and log to DB.
    """
    from core.models.recruitment import EmailLog
    from integrations.google.gmail import GmailService
    import logging
    logger = logging.getLogger("harvey")

    org = get_org(user)
    if not org:
        raise ValueError("User not associated with organization.")

    # ✍️ Append signature
    signature = get_email_signature(user)
    final_body = f"{body.rstrip()}\n\n{signature}"

    # 🧾 Log to DB
    EmailLog.objects.create(
        organization=org,
        recipient_email=recipient_email,
        subject=subject,
        body=final_body,
        status="sent"
    )

    # 📧 Send via Gmail
    service = GmailService(user=user)
    service.send_email(recipient_email, subject, final_body)
    logger.info(f"[HELPER] Email sent to {recipient_email}")
    return True

def get_user_timezone(user, org=None):
    """
    Fetch the appropriate timezone for a user.
    Priority: Organization Timezone -> Google Calendar Settings -> Asia/Kolkata
    """
    if not org:
        org = get_org(user)
    
    if org and getattr(org, 'timezone', None):
        return org.timezone
        
    try:
        from integrations.google.calendar import CalendarService
        from googleapiclient.discovery import build
        service = CalendarService(user=user)
        google_service = build("calendar", "v3", credentials=service.get_credentials())
        return google_service.settings().get(setting="timezone").execute()["value"]
    except Exception:
        return "Asia/Kolkata"

def create_calendar_event_helper(
    title,
    start_dt,
    end_dt,
    attendees_list,
    description,
    user,
    tz=None
):
    """
    Centralized helper to create Google Calendar events
    using explicit timezone handling (enterprise-safe).
    """

    from integrations.google.calendar import CalendarService
    from googleapiclient.discovery import build
    import pytz
    import logging

    logger = logging.getLogger("harvey")

    org = get_org(user)

    # 🔹 Determine Target Timezone
    if not tz:
        tz = get_user_timezone(user, org)

    # 🔹 Create service once
    service = CalendarService(user=user)

    # 🔹 Build Google service once (no double init)
    google_service = build("calendar", "v3", credentials=service.get_credentials())

    if tz == "Asia/Kolkata":
        try:
            tz = google_service.settings().get(setting="timezone").execute()["value"]
        except Exception:
            pass
            
    try:
        tz_obj = pytz.timezone(tz)
    except pytz.UnknownTimeZoneError:
        tz_obj = pytz.timezone("Asia/Kolkata")
        tz = "Asia/Kolkata"

    # Convert to the target timezone just to be safe, then strip tzinfo for Google API format
    final_start = start_dt.astimezone(tz_obj).replace(tzinfo=None)
    final_end = end_dt.astimezone(tz_obj).replace(tzinfo=None)

    final_start_str = final_start.strftime("%Y-%m-%dT%H:%M:%S")
    final_end_str = final_end.strftime("%Y-%m-%dT%H:%M:%S")

    att_str = ",".join(attendees_list) if isinstance(attendees_list, list) else (attendees_list or "")

    event_result = service.create_event(
        title=title,
        start_time=final_start_str,
        end_time=final_end_str,
        description=description,
        attendees=att_str,
        timezone=tz
    )
    
    logger.info(f"[HELPER] Calendar event created: {title} at {final_start_str} (TZ: {tz})")
    return event_result, tz