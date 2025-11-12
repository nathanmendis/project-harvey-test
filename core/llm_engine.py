# llm_engine.py
import json
from pydantic import BaseModel
from .agent import get_harvey_agent
from .models import Conversation, Message
from .actions import execute_action, ActionResult
from .redis_utils import get_user_memory, set_user_memory, clear_user_memory
from .utils.extractors import (
    extract_email_fields, extract_candidate_fields,
    extract_event_fields, extract_interview_fields
)


# Response Wrapper
class LLMResponse(BaseModel):
    response: str
    success: bool = True


# Main entry point
def generate_llm_reply(prompt: str, user=None):
    """Central LLM handler: reasoning + memory + execution."""
    if user is None:
        raise ValueError("User must be provided for Redis-backed memory.")

    memory_state = get_user_memory(user.id)
    agent = get_harvey_agent(user=user)

    # Ensure conversation exists
    conversation, _ = Conversation.objects.get_or_create(
        organization=user.organization,
        user=user,
        defaults={"title": "Chat Session"},
    )

    try:
        response = agent.invoke({"input": prompt})
        response_text = response.get("text") if isinstance(response, dict) else str(response)
    except Exception as e:
        response_text = f"⚠️ Gemini error: {e}"

    updated_memory = update_memory_state(memory_state, prompt, response_text)
    set_user_memory(user.id, updated_memory)

    next_step = decide_next_step(updated_memory, prompt, user)
    if next_step:
        response_text += f"\n\n{next_step}"

    # Log chat
    Message.objects.create(organization=user.organization, conversation=conversation, sender="user", message_text=prompt)
    Message.objects.create(organization=user.organization, conversation=conversation, sender="ai", message_text=response_text)

    # Clear memory after confirmed success
    if any(kw in response_text.lower() for kw in ["✅", "successfully", "completed", "email sent"]) \
       and "not" not in response_text.lower():
        clear_user_memory(user.id)
        print(f"🧹 Cleared Redis memory for {user.username} after success")

    print(f"\n🧠 Redis Memory ({user.username}): {json.dumps(updated_memory, indent=2)}")
    print(f"🤖 Harvey: {response_text}\n")

    return LLMResponse(response=response_text, success=True)


# Memory Management
def update_memory_state(memory_state: dict, user_input: str, ai_response: str) -> dict:
    """Updates structured Redis memory safely."""
    memory_state = memory_state or {}
    context = memory_state.get("context", {})
    lowered = user_input.lower()

    intent_map = {
        "add_candidate": ["add candidate", "new candidate", "hire", "onboard"],
        "create_calendar_event": ["schedule", "meeting", "event", "calendar"],
        "send_email": ["send email", "email", "mail", "notify"],
        "create_job_description": ["create job", "job description", "add job"],
        "schedule_interview": ["interview", "schedule interview", "book interview"],
    }

    detected_intent = memory_state.get("last_intent")
    for intent, keywords in intent_map.items():
        if any(k in lowered for k in keywords):
            if intent != memory_state.get("last_intent"):
                print(f"🧠 Switched intent to '{intent}', resetting context.")
                context = {}
            detected_intent = intent
            memory_state["last_intent"] = intent
            break

    # Handle intents
    if detected_intent == "send_email":
        context.setdefault("send_email_data", {})
        fields = extract_email_fields(user_input)
        context["send_email_data"].update({k: v for k, v in fields.items() if v})

    elif detected_intent == "add_candidate":
        context.setdefault("add_candidate_data", {})
        fields = extract_candidate_fields(user_input)
        context["add_candidate_data"].update({k: v for k, v in fields.items() if v})

    elif detected_intent == "create_calendar_event":
        context.setdefault("create_calendar_event_data", {})
        prev = context["create_calendar_event_data"]
        event_fields = extract_event_fields(user_input, existing_context=prev)
        context["create_calendar_event_data"].update(event_fields)

    elif detected_intent == "schedule_interview":
        context.setdefault("schedule_interview_data", {})
        prev = context["schedule_interview_data"]

    # 🧩 Extract new fields using previous context
        fields = extract_interview_fields(user_input, existing_context=prev)

    # Merge new fields into previous context
        for k, v in fields.items():
            if v:  # avoid overwriting with None
                prev[k] = v

    # ✅ Normalize candidate_id
        if "candidate_id" in prev and prev["candidate_id"]:
            try:
                prev["candidate_id"] = str(int(prev["candidate_id"]))  # safe numeric cast
            except Exception:
                prev["candidate_id"] = str(prev["candidate_id"]).strip()

        context["schedule_interview_data"] = prev

    
        print("🧠 DEBUG merged schedule_interview_data ->", context["schedule_interview_data"])



    # Confirmation
    if any(w in lowered for w in ["yes", "confirm", "go ahead", "done"]):
        context["confirmed"] = True

    memory_state["context"] = context
    return memory_state


# Decision Logic
def decide_next_step(memory_state: dict, user_input: str, user) -> str | None:
    """Checks if all required data is collected and executes action."""
    try:
        intent = memory_state.get("last_intent")
        if not intent:
            return None

        data_key = f"{intent}_data"
        context = memory_state.get("context", {})
        data = context.get(data_key, {})
        confirmed = context.get("confirmed", False)

        required = {
            "send_email": ["recipient", "subject", "body"],
            "add_candidate": ["name", "email"],
            "create_calendar_event": ["title", "date_time"],
            "schedule_interview": ["candidate_id", "when"],
            "create_job_description": ["title", "requirements"],
        }

        missing = [f for f in required.get(intent, []) if not data.get(f)]
        if missing:
            return f"I still need the following for {intent.replace('_', ' ')}: {', '.join(missing)}."

        if not confirmed:
            return f"I have all details for {intent.replace('_', ' ')}. Should I go ahead?"

        payload = {"fields": data}
        result: ActionResult = execute_action(intent, payload, user)
        return f"✅ {result.message}"

    except Exception as e:
        return f"⚠️ Error in decision logic: {e}"
