import logging
from langchain_core.messages import HumanMessage
from django.contrib.auth import get_user_model

logger = logging.getLogger("harvey")
User = get_user_model()

def _content_to_plaintext(msg):
    content = msg.content
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            c.get("text", "")
            for c in content
            if isinstance(c, dict) and c.get("type") == "text"
        )
    return str(content)

def get_state_value(state, key, default=None):
    """Work for both HarveyState objects and plain dicts"""
    if hasattr(state, key):
        return getattr(state, key, default)
    return state.get(key, default)

def set_state_value(state, key, value):
    """Update value no matter the state type"""
    if hasattr(state, key):
        setattr(state, key, value)
    else:
        state[key] = value

def append_trace(state, entry):
    trace = get_state_value(state, "trace", [])
    trace.append(entry)
    set_state_value(state, "trace", trace)

def get_user(state):
    """Retrieve user object from state using user_id"""
    user_id = get_state_value(state, "user_id")
    if user_id:
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            logger.error(f"User with id {user_id} not found.")
            return None
    return None

def log_token_usage(response, model_label):
    """Extract and log token usage from AIMessage metadata."""
    if hasattr(response, "response_metadata"):
        usage = response.response_metadata.get("token_usage")
        if usage:
            prompt = usage.get("prompt_tokens", 0)
            completion = usage.get("completion_tokens", 0)
            total = usage.get("total_tokens", 0)
            logger.info(f"-> [TOKENS] {model_label} (Prompt: {prompt}, Completion: {completion}, Total: {total})")
