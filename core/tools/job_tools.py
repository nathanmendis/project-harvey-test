# core/actions/job_tools.py
from ..models import JobRole
from .base import ActionResult
def create_job_description(payload, user):
    fields = payload.get("fields", {}) or {}
    org = getattr(user, "organization", None)

    title = fields.get("title")
    desc = fields.get("description", "")
    reqs = fields.get("requirements", "")
    dept = fields.get("department", "General")

    job = JobRole.objects.create(
        organization=org,
        title=title,
        description=desc,
        requirements=reqs,
        department=dept,
    )

    return ActionResult(
        ok=True,
        message=f"✅ Job role '{title}' created successfully in {dept} department."
    )
