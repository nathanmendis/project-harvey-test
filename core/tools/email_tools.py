# core/actions/email_tools.py
from ..models import EmailLog
from .base import ActionResult


def send_email(payload, user):
    from core.agent import get_harvey_agent 
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

def generate_email(payload, user=None):
    """
    Generates a professional HR-style email draft using Gemini.
    Expected payload format:
        {
            "fields": {
                "topic": "onboarding completion",
                "tone": "formal",
                "recipient": "hr@company.com"
            }
        }
    Returns an ActionResult with generated subject and body.
    """
    from core.agent import get_harvey_agent 
    try:
        fields = payload.get("fields", {}) or {}
        topic = fields.get("topic") or "General HR communication"
        tone = fields.get("tone", "formal professional")
        recipient = fields.get("recipient")

        # ✅ Use your existing Gemini agent
        agent = get_harvey_agent(user=user)

        prompt = (
            f"Write a short, {tone} HR email about '{topic}'. "
            "Include a clear subject line and a concise body (under 100 words). "
            "Respond in JSON with keys 'subject' and 'body'."
        )

        response = agent.invoke({"input": prompt})
        text = response.get("text") if isinstance(response, dict) else str(response)

        import json
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            data = {"subject": "Generated Email", "body": text}

        subject = data.get("subject", "Generated Email")
        body = data.get("body", text)

        msg = f"📧 Draft generated for {recipient or 'unspecified recipient'}:\n\n**Subject:** {subject}\n**Body:**\n{body}"
        return ActionResult(ok=True, message=msg, data={"subject": subject, "body": body})

    except Exception as e:
        return ActionResult(ok=False, message=f"⚠️ Error generating email: {e}")