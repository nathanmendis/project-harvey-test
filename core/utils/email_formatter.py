# email_formatter.py
import re
from typing import Optional, Tuple


# ============================================================
#       PROFESSIONAL TONE CONVERTER
# ============================================================
def make_professional(text: str) -> str:
    """
    Convert rough / informal text into a clean,
    formal, professional corporate email tone.
    """

    if not text:
        return ""

    # Normalize spacing
    text = re.sub(r"\s+", " ", text).strip()

    # Ensure sentence finishes properly
    if text and text[-1] not in ".!?":
        text += "."

    # Replace casual phrasing
    replacements = {
        r"\bok\b": "okay",
        r"\bokk\b": "okay",
        r"\bpls\b|\bplz\b": "please",
        r"\bthanks\b": "thank you",
        r"\bthank u\b": "thank you",
        r"\bhey\b": "Hello",
        r"\bhi\b": "Hello",
        r"\bkindly\b": "please",
        r"\bgonna\b": "going to",
        r"\bwanna\b": "want to",
        r"\bgotta\b": "have to",
    }

    for pattern, repl in replacements.items():
        text = re.sub(pattern, repl, text, flags=re.IGNORECASE)

    # Capitalize first letter
    if text:
        text = text[0].upper() + text[1:]

    return text


# ============================================================
#       BASIC CLEANERS
# ============================================================
def clean_subject(text: str) -> str:
    """Normalize and clean subject line."""
    text = text.strip()
    text = re.sub(r"^(subject[:\-]?)\s*", "", text, flags=re.IGNORECASE)

    if text:
        text = text[0].upper() + text[1:]

    return text


def fix_email_body(body: str) -> str:
    """Cleanup whitespace, duplicates, repeated headers."""
    if not body:
        return ""

    # Remove repeated "Dear <name>"
    body = re.sub(
        r"(Dear\s+[A-Za-z]+,?).*?(?=Dear\s+[A-Za-z]+,?)",
        r"\1\n",
        body,
        flags=re.IGNORECASE | re.DOTALL,
    )

    # Normalize line breaks
    body = re.sub(r"\n{3,}", "\n\n", body)

    # Strip each line
    lines = [line.strip() for line in body.split("\n")]
    body = "\n".join(lines)

    return body.strip()


# ============================================================
#       SUBJECT EXTRACTION
# ============================================================
def extract_subject_from_ai(ai_text: str) -> Optional[str]:
    """Extract subject from an LLM-drafted email."""
    if not ai_text:
        return None

    # Explicit Subject line
    m = re.search(r"subject[:\-]\s*(.+)", ai_text, re.IGNORECASE)
    if m:
        return clean_subject(m.group(1).strip())

    # First line looks like a subject (short, no "Dear")
    lines = ai_text.strip().split("\n")
    first = lines[0].strip()

    if len(first.split()) <= 10 and not first.lower().startswith("dear"):
        return clean_subject(first)

    return None


# ============================================================
#       BODY EXTRACTION
# ============================================================
def extract_body_from_ai(ai_text: str) -> Optional[str]:
    """Extract email body from AI's messy output."""
    if not ai_text:
        return None

    # Body beginning with "Dear ..."
    m = re.search(r"\bDear\b", ai_text, re.IGNORECASE)
    if m:
        idx = m.start()
        body = ai_text[idx:].strip()
        return make_professional(fix_email_body(body))

    # Body: section
    m = re.search(r"body[:\-]\s*(.+)", ai_text, re.IGNORECASE | re.DOTALL)
    if m:
        return make_professional(fix_email_body(m.group(1).strip()))

    # Fallback: treat full output as body
    return make_professional(fix_email_body(ai_text.strip()))


# ============================================================
#       MAIN FORMATTER
# ============================================================
def format_email(ai_text: str) -> Tuple[str, str]:
    """
    Returns (subject, body)
    Ensures professional tone even if AI output is messy.
    """
    subject = extract_subject_from_ai(ai_text)
    body = extract_body_from_ai(ai_text)

    # Auto-generate subject from first usable sentence
    if not subject:
        first_line = body.split("\n")[0].strip()

        # Skip greeting
        if first_line.lower().startswith("dear") and "\n" in body:
            first_line = body.split("\n")[1][:60].strip()

        subject = clean_subject(first_line[:60])

    return subject, body
