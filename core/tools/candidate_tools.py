# core/actions/candidate_tools.py
from ..models import Candidate
from .base import ActionResult

def add_candidate(payload, user):
    fields = payload.get("fields", {}) or {}
    org = getattr(user, "organization", None)

    name = fields.get("name")
    email = fields.get("email")
    phone = fields.get("phone")
    source = fields.get("source", "Chatbot")
    skills = fields.get("skills", [])

    if isinstance(skills, str):
        skills = [s.strip() for s in skills.split(",")]

    if Candidate.objects.filter(email=email, organization=org).exists():
        return ActionResult(ok=True, message=f"ℹ️ Candidate '{email}' already exists.")

    Candidate.objects.create(
        organization=org,
        name=name,
        email=email,
        phone=phone,
        skills=skills,
        source=source,
        status="pending",
    )

    return ActionResult(ok=True, message=f"✅ Candidate '{name}' added successfully.")


def shortlist_candidates(payload, user):
    """Later: use embeddings/vector DB to shortlist."""
    fields = payload.get("fields", {}) or {}
    org = getattr(user, "organization", None)
    skills = fields.get("skills", [])
    limit = int(fields.get("limit", 5))

    if isinstance(skills, str):
        skills = [s.strip().lower() for s in skills.split(",")]

    candidates = Candidate.objects.filter(organization=org)
    filtered = [
        c for c in candidates
        if any(skill.lower() in (",".join(c.skills or [])).lower() for skill in skills)
    ][:limit]

    names = [c.name for c in filtered]
    return ActionResult(ok=True, message=f"🎯 Shortlisted candidates: {', '.join(names) or 'none found'}.")
