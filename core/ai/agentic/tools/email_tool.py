from langchain.tools import tool
import json
from core.models.recruitment import EmailLog
from django.contrib.auth import get_user_model
User = get_user_model()
import re
from django.db.models import Q
EMAIL_REGEX = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"

def is_valid_email(value: str) -> bool:
    return bool(re.match(EMAIL_REGEX, value))
def resolve_recipient_email(raw_recipient: str, user):
    """
    Resolve recipient from:
    - valid email
    - username
    - name (partial match)
    scoped to the user's organization
    """
    

    if not raw_recipient:
        return None

    raw_recipient = raw_recipient.strip()

    # Case 1: Already a valid email
    if is_valid_email(raw_recipient):
        
        return raw_recipient

    # Case 2: Try resolving inside org
    if user and getattr(user, "organization", None):
        qs = User.objects.filter(
            organization=user.organization
        ).filter(
            Q(username__iexact=raw_recipient) |
            Q(name__icontains=raw_recipient)
        )

        

        match = qs.first()
        if match:
         

        if match and match.email and is_valid_email(match.email):
           
            return match.email

    
    return None
def get_email_signature(user):
 

    lines = ["Regards,"]

    name = (
        getattr(user, "name", None)
        or getattr(user, "get_full_name", lambda: None)()
        or getattr(user, "username", None)
        or "Team"
    )
    lines.append(name)

    role_map = {
        "employee": "Employee",
        "manager": "Manager",
        "hr": "HR Team",
        "org_admin": "Organization Admin",
    }
    role = role_map.get(getattr(user, "role", None))
    if role:
        lines.append(role)

    organization = getattr(user, "organization", None)
    if organization and getattr(organization, "name", None):
        lines.append(organization.name)

    email = getattr(user, "email", None)
    if email:
        lines.append(f"Email: {email}")

    signature = "\n".join(lines)


    return signature

    
    
@tool
def send_email_tool(recipient_email: str, subject: str, body: str, user=None) -> str:
    """
    Send an email to a recipient.
    Resolves usernames or names to email addresses within the organization,
    appends a professional signature, and sends via Gmail.
    """


    user = user or get_user()
   

    # 🔍 Resolve recipient
    resolved_email = resolve_recipient_email(recipient_email, user)
  

    if not resolved_email:
       
        return json.dumps({
            "status": "error",
            "ok": False,
            "message": (
                f"Could not resolve recipient '{recipient_email}' to a valid email. "
                "Please provide a valid email address or a known user name."
            )
        })

    # ✍️ Append signature
    if user:
        signature = get_email_signature(user)
        final_body = f"{body.rstrip()}\n\n{signature}"
    else:
        final_body = f"{body.rstrip()}\n\nRegards,\nTeam"

    # 🧾 Log to DB
    if user and getattr(user, "organization", None):
       
        EmailLog.objects.create(
            organization=user.organization,
            recipient_email=resolved_email,
            subject=subject,
            body=final_body,
            status="sent"
        )

    try:
       
        from integrations.google.gmail import GmailService
        service = GmailService(user=user)
        service.send_email(resolved_email, subject, final_body)

 

        return json.dumps({
            "status": "success",
            "ok": True,
            "message": f"Email sent to {resolved_email}",
            "details": {
                "recipient": resolved_email,
                "subject": subject
            }
        })

    except Exception as e:
 
        return json.dumps({
            "status": "error",
            "ok": False,
            "message": f"Failed to send email: {str(e)}"
        })