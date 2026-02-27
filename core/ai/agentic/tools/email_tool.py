from langchain.tools import tool
import json
from core.models.recruitment import EmailLog
from .utils import ok, err, get_org, is_valid_email, resolve_user_emails, get_email_signature

@tool
def send_email_tool(recipient_email: str, subject: str, body: str, user=None) -> str:
    """
    Send an email to a recipient.
    Resolves usernames or names to email addresses within the organization,
    appends a professional signature, and sends via Gmail.
    """
    org = get_org(user)
    if not org:
        return err("User is not associated with any organization. Please contact support.")

    # 🔍 Resolve recipient
    emails = resolve_user_emails(recipient_email, org)
  
    if not emails:
        return err(
            f"Could not resolve recipient '{recipient_email}' to a valid email. "
            "Please provide a valid email address or a known user name."
        )

    if len(emails) > 1:
        return err(
            f"Multiple users found matching '{recipient_email}': {', '.join(emails)}. "
            "Please provide a more specific name or the exact email address."
        )

    resolved_email = emails[0]

    if not is_valid_email(resolved_email):
        return err(f"Resolved email '{resolved_email}' is invalid.")

    try:
        from .utils import send_email_helper
        send_email_helper(
            recipient_email=resolved_email,
            subject=subject,
            body=body,
            user=user
        )

        return ok(f"Email sent to {resolved_email}", recipient=resolved_email, subject=subject)

    except Exception as e:
        return err(f"Failed to send email: {str(e)}")
