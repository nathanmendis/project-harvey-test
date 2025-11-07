# core/actions/email_tools.py
from ..models import EmailLog
from .base import ActionResult
def send_email(payload, user):
    fields = payload.get("fields", {}) or {}
    org = getattr(user, "organization", None)

    recipient = fields.get("recipient")
    subject = fields.get("subject", "(No Subject)")
    body = fields.get("body", "(No Body)")

    EmailLog.objects.create(
        organization=org,
        recipient_email=recipient,
        subject=subject,
        body=body,
        status="sent",
    )

    return ActionResult(ok=True, message=f"📧 Email logged to {recipient} — subject: '{subject}'.")
