from langchain.tools import tool
import json

@tool
def send_email_tool(recipient_email: str, subject: str, body: str) -> str:
    """
    Send an email to a recipient.
    Use this tool when the user asks to send an email.
    """
    # Placeholder: In the future, this will resolve the user's preferred provider
    # and use the appropriate EmailService (Google/Microsoft).
    
    # For now, we just return a success message to simulate the action.
    return json.dumps({
        "status": "success",
        "message": f"Email sent to {recipient_email}",
        "details": {
            "recipient": recipient_email,
            "subject": subject
        }
    })
