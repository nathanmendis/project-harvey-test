import re

FILLERS = {
    "yes", "ok", "okay", "done", "confirm", "yup", "sure",
    "send", "send it", "go ahead", "yeah", "alright"
}

def extract_email(text: str):
    """Extract first email address from text."""
    m = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", text)
    return m.group(0) if m else None


def extract_email_fields(text: str):
    """
    Extract recipient + possible natural-language email body.
    Does NOT create subject (left to AI formatter).
    """
    cleaned = text.strip()
    lowered = cleaned.lower()

    recipient = extract_email(cleaned)

    # ---------------------------------------------
    # Extract body (ONLY IF meaningful user content)
    # ---------------------------------------------
    body = None

    if recipient:
        # Remove email from the message
        without_email = cleaned.replace(recipient, "").strip()

        # Common prefixes after email:
        prefixes = [
            "inform", "informing", "tell", "telling",
            "that", "to", "please", "kindly", "let him know",
            "message", "email", "write", "draft"
        ]
        if any(p in without_email.lower() for p in prefixes):
            body = without_email

            # Must be meaningful
            if len(body.split()) <= 3 or body.lower() in FILLERS:
                body = None
    else:
        # No email present → user may be dictating email content?
        if cleaned.lower() not in FILLERS and len(cleaned.split()) > 3:
            body = cleaned

    # ---------------------------------------------
    # Build result
    # ---------------------------------------------
    result = {}

    if recipient:
        result["recipient"] = recipient

    if body:
        result["body"] = body

    # Subject intentionally NOT included → let formatter handle it
    return result
