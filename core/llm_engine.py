# core/llm_engine.py
import json
import re
from typing import Dict, Optional
from pydantic import BaseModel

from .agent import get_harvey_agent
from .models import Conversation, Message
from .actions import execute_action, ActionResult
from .redis_utils import get_user_memory, set_user_memory, clear_user_memory

from .utils.extractors import (
    extract_email_fields,
    extract_candidate_fields,
    extract_event_fields,
    extract_interview_fields,
)


from .utils.email_formatter import format_email


class LLMResponse(BaseModel):
    response: str
    success: bool = True


CONFIRM_TOKENS = {"yes", "ok", "okay", "confirm", "go ahead", "yup", "sure", "send it"}
GENERIC_TOKENS = {"hi", "hello", "thanks", "thank you", "what's up", "how are you", "what time is it", "good morning", "good evening"}
# CHANGED: Lowered threshold to 1. Any detected intent keyword will trigger a context switch.
SWITCH_THRESHOLD = 1 

def _is_strict_confirmation(message: Optional[str]) -> bool:
    """Return True only if message is exactly a confirmation token (after stripping)."""
    if not message:
        return False
    m = message.strip().lower()
    return m in CONFIRM_TOKENS


def _looks_like_placeholder_subject(subj: Optional[str]) -> bool:
    if not subj:
        return True
    s = subj.strip().lower()
    return s in ("message", "", "subject")


def _looks_like_user_command_body(body: Optional[str], user_input: str) -> bool:
    """Detect cases where 'body' is actually a repetition of user command like 'send an email to ...'"""
    if not body:
        return False
    
    bi = body.strip().lower()
    ui = (user_input or "").strip().lower()
    if not ui:
        return False
    # Check if the body is an exact command repetition or starts with a large chunk of the command
    return ui in bi or bi.startswith(ui[:50])


def generate_llm_reply(prompt: str, user=None):
    if not user:
        raise ValueError("User must be provided for Redis memory.")

    memory_state = get_user_memory(user.id) or {}
    agent = get_harvey_agent(user=user)

    conversation, _ = Conversation.objects.get_or_create(
        organization=user.organization,
        user=user,
        defaults={"title": "Chat Session"},
    )

    # run model
    try:
        response = agent.invoke({"input": prompt})
        ai_text = response.get("text") if isinstance(response, dict) else str(response)
    except Exception as e:
        ai_text = f"⚠️ Model error: {e}"

    
    memory_state = memory_state or {}
    memory_state["last_ai"] = ai_text
    
    memory_state["last_user_input"] = (prompt or "").strip()

    # update memory
    updated = update_memory_state(memory_state, prompt, ai_text)
    set_user_memory(user.id, updated)

    
    follow_up = decide_next_step(updated, prompt, user)
    if follow_up:
        ai_text += "\n\n" + follow_up

    
    Message.objects.create(
        organization=user.organization,
        conversation=conversation,
        sender="user",
        message_text=prompt,
    )
    Message.objects.create(
        organization=user.organization,
        conversation=conversation,
        sender="ai",
        message_text=ai_text,
    )

    
    # Check for successful completion keywords to clear memory
    if any(x in ai_text.lower() for x in ["successfully", "completed", "email sent", "scheduled"]) and "not" not in ai_text.lower():
        clear_user_memory(user.id)
        print(f"🧹 Cleared memory for {user.username}")

    print("\n🧠 Redis Memory:", json.dumps(updated, indent=2))
    print("🤖 Harvey:", ai_text)

    return LLMResponse(response=ai_text, success=True)


def update_memory_state(memory_state: Dict, user_input: str, ai_response: str) -> Dict:
    """
    Update structured memory with improved intent switching logic.
    """
    memory_state = memory_state or {}
    context = memory_state.get("context", {}) or {}
    lowered = (user_input or "").lower().strip()

    intent_keywords = {
        "add_candidate": ["add candidate", "new candidate", "hire", "onboard", "candidate name", "candidate email"],
        "create_calendar_event": ["schedule a meeting", "schedule meeting", "meeting with", "book meeting", "event", "calendar"],
        "send_email": ["send an email", "send email to", "write an email", "draft an email", "email to", "compose email"],
        "schedule_interview": ["schedule interview", "book interview", "interview with", "set up interview"],
        "create_job_description": ["job description", "create job", "add job"],
    }

    last_intent = memory_state.get("last_intent")

    # simple scoring
    scores = {intent: 0 for intent in intent_keywords}
    for intent, keys in intent_keywords.items():
        for k in keys:
            if k in lowered:
                scores[intent] += 1

    best_intent = max(scores, key=lambda k: scores[k])
    current_best_score = scores[best_intent]
    
    # --- 1. CONTEXT CLEARING / INTENT SWITCHING LOGIC ---
    detected_intent = last_intent # Start by assuming we stick to the last intent

    # Check for generic/irrelevant messages or zero-score input (Clears context if user wanders)
    if current_best_score == 0 and lowered in GENERIC_TOKENS:
        if last_intent:
            print(f"🧠 Cleared context due to generic input (was: {last_intent})")
            memory_state.pop("last_intent", None)
            memory_state.pop("context", None)
            return memory_state
    
    # Intent Switching Logic: If the new best intent scores high enough, it WINS
    if current_best_score >= SWITCH_THRESHOLD:
        if best_intent != last_intent:
            # Crucial: Reset context if a switch occurs
            print(f"🧠 Intent switched (High Confidence: {current_best_score}) -> {best_intent}")
            context = {} 
        detected_intent = best_intent
    elif current_best_score > 0 and last_intent is None:
        # Set initial intent if one is detected
        detected_intent = best_intent
    # If score is low (< threshold) and we have a last_intent, we stick to last_intent to fill context.
    
    memory_state["last_intent"] = detected_intent

    if not detected_intent:
        memory_state["context"] = context
        return memory_state

   
    if detected_intent == "send_email":
        ctx = context.setdefault("send_email_data", {})
        fields = extract_email_fields(user_input)

        
        # 1. Update fields extracted from the user's input (PRIORITIZED)
        for k, v in fields.items():
            if not v:
                continue
            if k in ("subject", "body"):
                if k == "subject" and len(v.split()) > 1 and not _looks_like_placeholder_subject(v):
                    ctx["subject"] = v
                # CHANGED: Relaxed body check - only check for command repetition
                if k == "body" and not _looks_like_user_command_body(v, user_input):
                    ctx["body"] = v
                
            else:
                ctx[k] = v

        # 2. Use format_email(ai_response) as a FALLBACK if subject/body are still MISSING.
        if not ctx.get("subject") or not ctx.get("body"):
            try:
                subj, body = format_email(ai_response)
            except Exception:
                subj, body = None, None

            if subj and not ctx.get("subject"):
                ctx["subject"] = subj

            if body and not ctx.get("body"):
                if not _looks_like_user_command_body(body, user_input):
                    ctx["body"] = body


        context["send_email_data"] = ctx

    elif detected_intent == "add_candidate":
        ctx = context.setdefault("add_candidate_data", {})
        fields = extract_candidate_fields(user_input)
        for k, v in fields.items():
            if v:
                ctx[k] = v
        context["add_candidate_data"] = ctx

    elif detected_intent == "create_calendar_event":
        ctx = context.setdefault("create_calendar_event_data", {})
        prev = ctx.copy()
        new_fields = extract_event_fields(user_input, existing_context=prev)
       
        if new_fields.get("title", "").lower() in ("one hour", "an hour", "hour"):
            new_fields.pop("title", None)
        for k, v in new_fields.items():
            if v is not None:
                prev[k] = v
        context["create_calendar_event_data"] = prev

    elif detected_intent == "schedule_interview":
        ctx = context.setdefault("schedule_interview_data", {})
        prev = ctx.copy()
        new_fields = extract_interview_fields(user_input, existing_context=prev)
        for k, v in new_fields.items():
            if v is not None:
                prev[k] = v
        # normalize candidate id
        if "candidate_id" in prev and prev["candidate_id"] is not None:
            try:
                prev["candidate_id"] = str(int(prev["candidate_id"]))
            except Exception:
                prev["candidate_id"] = str(prev["candidate_id"]).strip()
        context["schedule_interview_data"] = prev

 
    # Handle explicit confirmation
    last_user = (memory_state.get("last_user_input") or "").strip()
    if _is_strict_confirmation(last_user):
        # set confirmed only when the raw user message was exactly a confirmation token
        context["confirmed"] = True
    else:    
        context.pop("confirmed", None)

    memory_state["context"] = context
    return memory_state


def decide_next_step(memory_state: Dict, user_input: str, user) -> Optional[str]:
    try:
        intent = memory_state.get("last_intent")
        if not intent:
            return None

        ctx = memory_state.get("context", {}) or {}
        data = ctx.get(f"{intent}_data", {})
        confirmed = ctx.get("confirmed", False)

        required = {
            "send_email": ["recipient", "subject", "body"],
            "add_candidate": ["name", "email","skills"],
            "create_calendar_event": ["title", "date_time"],
            "schedule_interview": ["candidate_id", "when"],
            "create_job_description": ["title", "requirements"],
        }

        if intent not in required:
            return None

        missing = [k for k in required[intent] if not data.get(k)]
        if missing:
            return f"I still need: {', '.join(missing)} for {intent.replace('_', ' ')}."

        
        last_user = (memory_state.get("last_user_input") or "").strip()
        if not confirmed or not _is_strict_confirmation(last_user):
            return f"I have all details for {intent.replace('_', ' ')}. Should I go ahead?"

        
        if intent == "send_email":
            subj = data.get("subject", "")
            body = data.get("body", "")
            if _looks_like_placeholder_subject(subj):
                return "⚠️ The email subject looks like a placeholder. Please provide a clear subject."
            if not body:
                 return "⚠️ The email body is empty. Please provide the email body or ask me to draft it."


        
        result: ActionResult = execute_action(intent, {"fields": data}, user)
        return f"✅ {result.message}"

    except Exception as e:
        return f"⚠️ Error in decision logic: {e}"