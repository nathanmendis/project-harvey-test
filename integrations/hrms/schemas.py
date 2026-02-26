"""
HRMS Endpoint Schema Registry.

Defines the required and optional fields for each harvestable model.
Used to validate a user-provided sample JSON response before persisting
a dynamic HRMSEndpointMapping.
"""

import json
from typing import Any

# --------------------------------------------------------------------- #
#  Schema Registry                                                        #
# --------------------------------------------------------------------- #

MODEL_SCHEMAS: dict[str, dict[str, list[str]]] = {
    "Employee": {
        "required": ["email"],
        "optional": ["first_name", "last_name", "name", "phone"],
    },
    "Candidate": {
        "required": ["email", "name"],
        "optional": ["phone", "status", "skills", "source"],
    },
    "Interview": {
        "required": ["candidate_id", "scheduled_at"],
        "optional": ["interviewers", "status"],
    },
    "LeaveRequest": {
        "required": ["employee_id", "start_date", "end_date", "leave_type"],
        "optional": ["status", "notes"],
    },
    "JobRole": {
        "required": ["title"],
        "optional": ["department", "description", "requirements", "status"],
    },
}


# --------------------------------------------------------------------- #
#  Validation Helper                                                      #
# --------------------------------------------------------------------- #

def validate_sample_json(target_model: str, raw_json: str) -> dict[str, Any]:
    """
    Validate a raw JSON sample string against the schema for *target_model*.

    Returns a dict with:
        - valid (bool):        True if all required fields are present.
        - matched   (list):    Required fields that were found.
        - missing   (list):    Required fields that were NOT found.
        - unknown   (list):    Keys present in the sample but not in schema.
        - error     (str|None):Parse/type error message, if any.
    """
    schema = MODEL_SCHEMAS.get(target_model)
    if not schema:
        return {"valid": False, "error": f"No schema registered for model '{target_model}'."}

    # Try to parse JSON
    try:
        sample = json.loads(raw_json)
    except (json.JSONDecodeError, TypeError) as exc:
        return {"valid": False, "error": f"Invalid JSON: {exc}"}

    # Accept either a single object or a list – inspect the first item
    if isinstance(sample, list):
        if not sample:
            return {"valid": False, "error": "Sample JSON array is empty."}
        sample = sample[0]

    if not isinstance(sample, dict):
        return {"valid": False, "error": "Sample JSON must be an object or array of objects."}

    sample_keys = set(sample.keys())
    required = set(schema["required"])
    optional = set(schema.get("optional", []))
    all_known = required | optional

    matched = sorted(required & sample_keys)
    missing = sorted(required - sample_keys)
    unknown = sorted(sample_keys - all_known)

    return {
        "valid": len(missing) == 0,
        "matched": matched,
        "missing": missing,
        "unknown": unknown,
        "error": None,
    }
