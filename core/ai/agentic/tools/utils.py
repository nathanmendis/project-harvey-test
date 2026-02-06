import json
import re
from django.db.models import Q
from django.contrib.auth import get_user_model

User = get_user_model()
EMAIL_REGEX = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"

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
