import json
from typing import Optional, Dict, Any
from google import genai
from django.conf import settings

# 🧠 Strict schema (all key fields required)
INTENT_SCHEMA = {
    "create_job_description": {
        "required": ["title", "description", "requirements", "department"],
        "optional": [],
    },
    "add_candidate": {
        "required": ["name", "email", "phone", "skills", "source"],
        "optional": [],
    },
    "shortlist_candidates": {
        "required": ["skills"],
        "optional": ["limit"],
    },
    "schedule_interview": {
        "required": ["candidate_id", "when", "interviewer_id", "duration_minutes", "location_link"],
        "optional": [],
    },
    "send_email": {
        "required": ["recipient", "subject", "body"],
        "optional": [],
    },
}

INTENT_SYSTEM_PROMPT = """
You are Harvey's intent parser.
Your job is to extract structured data from user messages into JSON format.

Always return a JSON object:
{
  "intent": "<intent_name>",
  "fields": { <key-value pairs> },
  "missing_fields": [ <list of missing required fields> ]
}

Rules:
- Use the provided schema for valid field names.
- Include all recognized fields present in the message.
- If any required field is missing, include it in `missing_fields`.
- Never repeat previously collected information.
- Return clean JSON only (no markdown, no text outside braces).
- If unsure, return: {"intent": "unknown", "fields": {}, "missing_fields": []}.
"""

_GENAI_CLIENT = None


def get_client():
    """Reuses or initializes the Gemini client."""
    global _GENAI_CLIENT
    if _GENAI_CLIENT is not None:
        return _GENAI_CLIENT

    api_key = getattr(settings, "GOOGLE_API_KEY", None)
    if not api_key:
        raise ValueError("GOOGLE_API_KEY missing from Django settings")

    _GENAI_CLIENT = genai.Client(api_key=api_key)
    return _GENAI_CLIENT


def parse_intent(user_message: str, context_fields: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """Strict, context-aware intent parser that only asks for missing fields once."""
    try:
        client = get_client()
        if not client:
            return {"intent": "unknown", "fields": {}, "missing_fields": []}

        prompt = f"{INTENT_SYSTEM_PROMPT}\nUser: {user_message}\nJSON:"
        resp = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)

        text = (resp.text or "").strip()
        first, last = text.find("{"), text.rfind("}")
        if first == -1 or last == -1:
            return None

        data = json.loads(text[first:last + 1])
        if not isinstance(data, dict) or "intent" not in data:
            return None

        intent_name = data["intent"]
        fields = data.get("fields", {}) or {}
        missing_fields = data.get("missing_fields", []) or []

        # ✅ Merge new fields with existing context (previously filled ones)
        if context_fields:
            for k, v in context_fields.items():
                if k not in fields or not fields[k]:
                    fields[k] = v

        if intent_name not in INTENT_SCHEMA and intent_name != "unknown":
            return {"intent": "unknown", "fields": {}, "missing_fields": []}

        schema = INTENT_SCHEMA.get(intent_name, {})
        required_fields = schema.get("required", [])

        # 🔍 Compute truly missing fields (after merge)
        computed_missing = [f for f in required_fields if not fields.get(f)]
        combined_missing = sorted(set(computed_missing + missing_fields))

        # 🟡 Still missing? Ask specifically for them once
        if combined_missing:
            clarification = ask_for_missing_fields(intent_name, combined_missing)
            return {
                "intent": intent_name,
                "fields": fields,
                "missing_fields": combined_missing,
                "clarification": clarification,
            }

        # ✅ All required fields complete — proceed
        return {
            "intent": intent_name,
            "fields": fields,
            "missing_fields": [],
        }

    except Exception as e:
        print(f"⚠️ Intent parsing error: {e}")
        return {"intent": "unknown", "fields": {}, "missing_fields": []}


def ask_for_missing_fields(intent_name: str, missing_fields: list) -> str:
    """Generate a clear, polite follow-up for missing fields."""
    try:
        client = get_client()
        if not client:
            return "Could you please provide the remaining details?"

        field_descriptions = {
            "email": "the candidate’s email address",
            "phone": "their phone number",
            "skills": "key skills or technologies",
            "name": "the candidate’s full name",
            "source": "where the candidate came from (e.g., referral, job portal)",
            "title": "the job title or position",
            "description": "a short job description",
            "requirements": "key qualifications or responsibilities",
            "department": "the department name",
            "when": "the interview date and time",
            "recipient": "the recipient’s email",
            "subject": "the email subject line",
            "body": "the email message content",
        }

        readable = [field_descriptions.get(f, f) for f in missing_fields]
        fields_text = ", ".join(readable)

        question_prompt = (
            f"You are Harvey, a helpful HR assistant.\n"
            f"The user is performing '{intent_name}'.\n"
            f"Ask one polite, concise question to collect: {fields_text}."
        )

        resp = client.models.generate_content(model="gemini-2.5-flash", contents=question_prompt)
        reply = (resp.text or "").strip()

        if not reply or not any(word in reply.lower() for word in ["please", "could", "share"]):
            reply = f"Could you please share {fields_text}?"
        return reply

    except Exception as e:
        print(f"⚠️ Clarification generation error: {e}")
        return "Could you please provide the missing details?"
