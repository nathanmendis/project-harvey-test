from langchain_core.tools import tool
from django.utils import timezone
from core.models.recruitment import EmailLog
from core.ai.agentic.tools.utils import ok, err, get_org, resolve_candidate_emails

@tool("send_email", return_direct=True)
def send_email(recipient: str, subject: str, body: str, user=None) -> str:
    """Logs a sent email to a candidate or employee."""
    org = get_org(user)
    if not org:
        return err("User is not associated with any organization. Please contact support.")

    # 🔍 Resolve recipient
    emails = resolve_candidate_emails(recipient, org)
    
    if not emails:
        return err(f"Could not resolve recipient '{recipient}' to a valid candidate email.")

    if len(emails) > 1:
        return err(f"Multiple candidates found matching '{recipient}': {', '.join(emails)}. Please be more specific.")

    resolved_email = emails[0]

    e = EmailLog.objects.create(
        organization=org,
        recipient_email=resolved_email,
        subject=subject,
        body=body,
        status="sent",
        sent_time=timezone.now(),
    )
    return ok(f"I've sent the email to {resolved_email} regarding '{subject}'.", log_id=e.id)
