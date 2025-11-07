# core/actions/interview_tools.py
from datetime import datetime
from django.utils.timezone import make_aware
from ..models import Interview, Candidate
from .base import ActionResult
from django.contrib.auth import get_user_model

User = get_user_model()


def schedule_interview(payload, user):
    fields = payload.get("fields", {}) or {}
    org = getattr(user, "organization", None)
    cand_id = fields.get("candidate_id")
    interviewer_id = fields.get("interviewer_id")
    when = fields.get("when")

    if not cand_id or not when:
        return ActionResult(ok=False, message="⚠️ Missing candidate_id or date/time.")

    candidate = Candidate.objects.filter(id=cand_id, organization=org).first()
    interviewer = User.objects.filter(id=interviewer_id).first() if interviewer_id else user

    if not candidate:
        return ActionResult(ok=False, message=f"❌ Candidate with ID {cand_id} not found.")

    dt = make_aware(datetime.fromisoformat(when))
    Interview.objects.create(
        organization=org,
        candidate=candidate,
        interviewer=interviewer,
        date_time=dt,
        status="scheduled",
    )
    return ActionResult(ok=True, message=f"✅ Interview scheduled for {candidate.name} on {when}.")
