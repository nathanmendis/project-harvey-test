import re
from .email_extractors import extract_email

def extract_candidate_fields(text: str):
    name = re.search(r"(?:name is|named)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)", text, re.IGNORECASE)
    email = extract_email(text)
    phone = re.search(r"\b\d{8,15}\b", text)
    role = re.search(r"(?:role|position)\s*(?:is|:)?\s*([A-Za-z ]+)", text)
    # NEW: Simple skills extraction
    skills_match = re.search(r"(?:skills|are|include)\s*(.+)", text, re.IGNORECASE)
    skills = skills_match.group(1).strip() if skills_match else None
    # Simple cleanup for skills list
    if skills:
        skills = skills.replace(" and ", ",").replace(", ,", ",")
        # Remove common trailing words
        skills = re.sub(r"(?:\.|\s*)$", "", skills).strip()

    return {
        "name": name.group(1) if name else None,
        "email": email,
        "phone": phone.group(0) if phone else None,
        "role": role.group(1).strip() if role else None,
        "skills": skills, # NEW: Added skills
    }
