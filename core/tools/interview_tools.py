# core/actions/interview_tools.py
from datetime import datetime
from ..models import Interview, Candidate
from .base import ActionResult
from django.contrib.auth import get_user_model
from django.utils.timezone import make_aware, is_aware, get_current_timezone
User = get_user_model()



def schedule_interview(payload, user):
    """
    Safely schedules an interview. Handles both timezone-aware and naive datetimes.
    """
    fields = payload.get("fields", {}) or {}
    org = getattr(user, "organization", None)
    cand_id = fields.get("candidate_id")
    interviewer_id = fields.get("interviewer_id")
    when = fields.get("when")
    duration = fields.get("duration_minutes", 60)  # default 1 hour

    if not cand_id or not when:
        return ActionResult(ok=False, message="⚠️ Missing candidate_id or date/time.")

    candidate = Candidate.objects.filter(id=cand_id, organization=org).first()
    interviewer = User.objects.filter(id=interviewer_id).first() if interviewer_id else user

    if not candidate:
        return ActionResult(ok=False, message=f"❌ Candidate with ID {cand_id} not found.")

    # --- Parse datetime safely ---
    try:
        dt = datetime.fromisoformat(when)
        if not is_aware(dt):
            dt = make_aware(dt, get_current_timezone())
    except Exception:
        return ActionResult(ok=False, message=f"⚠️ Invalid datetime format: {when}")

    # --- Create the interview record ---
    Interview.objects.create(
        organization=org,
        candidate=candidate,
        interviewer=interviewer,
        date_time=dt,
        status="scheduled",
       
    )

    local_time_str = dt.strftime("%b %d, %Y %I:%M %p")
    return ActionResult(ok=True, message=f"✅ Interview scheduled for {candidate.name} on {local_time_str}.")