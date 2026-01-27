from langchain.tools import tool
import json
from core.models.recruitment import EmailLog

@tool
def send_email_tool(recipient_email: str, subject: str, body: str, user=None) -> str:
    """
    Send an email to a recipient.
    Use this tool when the user asks to send an email.
    """
    # Placeholder: In the future, this will resolve the user's preferred provider
    # and use the appropriate EmailService (Google/Microsoft).
    
    # Log to DB if user context is available
    if user and hasattr(user, 'organization'):
        EmailLog.objects.create(
            organization=user.organization,
            recipient_email=recipient_email,
            subject=subject,
            body=body,
            status="sent"
        )
    
    # For now, we just return a success message to simulate the action.
    return json.dumps({
        "status": "success",
        "ok": True,
        "message": f"Email sent to {recipient_email}",
        "details": {
            "recipient": recipient_email,
            "subject": subject
        }
    })
