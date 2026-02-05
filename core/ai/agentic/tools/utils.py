import json

def ok(message, **data):
    return json.dumps({"ok": True, "message": message, **data})

def err(message):
    return json.dumps({"ok": False, "message": message})

def get_org(user):
    """Helper to get organization from user."""
    if user and getattr(user, "organization", None):
        return user.organization
    return None
