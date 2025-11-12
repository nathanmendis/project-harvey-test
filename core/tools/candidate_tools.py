# core/actions/candidate_tools.py
from ..models import Candidate
from .base import ActionResult


def add_candidate(payload, user):
    """
    Adds a candidate to the database.
    Accepts both {"fields": {...}} and flat payloads.
    Validates inputs and prevents duplicate entries.
    """
    org = getattr(user, "organization", None)
    if org is None:
        return ActionResult(ok=False, message="⚠️ User is not linked to any organization.")

    # 🧠 Normalize fields
    fields = payload.get("fields") if isinstance(payload.get("fields"), dict) else payload or {}
    name = (fields.get("name") or "").strip()
    email = (fields.get("email") or "").strip().lower()
    phone = (fields.get("phone") or "").strip() or None
    source = fields.get("source", "Chatbot").strip()
    skills = fields.get("skills", [])

    # 🧾 Basic validation
    if not name:
        return ActionResult(ok=False, message="⚠️ Missing candidate name.")
    if not email:
        return ActionResult(ok=False, message="⚠️ Missing candidate email address.")

    # 🧩 Normalize skills
    if isinstance(skills, str):
        skills = [s.strip() for s in skills.split(",") if s.strip()]
    elif isinstance(skills, list):
        skills = [s.strip() for s in skills if isinstance(s, str)]
    else:
        skills = []

    # 🔍 Check for duplicates
    existing = Candidate.objects.filter(email=email, organization=org).first()
    if existing:
        return ActionResult(ok=True, message=f"ℹ️ Candidate '{existing.name}' already exists.")

    # 🧱 Create candidate
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
    """
    Shortlists candidates based on provided skills.
    For now, uses simple string matching.
    Later, can be upgraded to embeddings/vector search.
    """
    org = getattr(user, "organization", None)
    if org is None:
        return ActionResult(ok=False, message="⚠️ User is not linked to any organization.")

    fields = payload.get("fields") or {}
    skills = fields.get("skills", [])
    limit = int(fields.get("limit", 5))

    # 🧠 Normalize skills list
    if isinstance(skills, str):
        skills = [s.strip().lower() for s in skills.split(",")]
    elif isinstance(skills, list):
        skills = [s.strip().lower() for s in skills if isinstance(s, str)]

    candidates = Candidate.objects.filter(organization=org)
    filtered = [
        c for c in candidates
        if any(skill in (",".join(c.skills or [])).lower() for skill in skills)
    ][:limit]

    if not filtered:
        return ActionResult(ok=True, message="⚠️ No matching candidates found.")

    names = ", ".join(c.name for c in filtered)
    return ActionResult(ok=True, message=f"🎯 Shortlisted candidates: {names}.")
