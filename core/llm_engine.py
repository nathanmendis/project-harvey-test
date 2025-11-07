from pydantic import BaseModel
from .intent import parse_intent, get_client
from .actions import execute_action, ActionResult
from .models import Conversation, Message
import json


class LLMResponse(BaseModel):
    response: str
    intent: str | None = None
    success: bool = True


def generate_llm_reply(prompt: str, user=None) -> LLMResponse:
    """
    Handles:
    - strict intent parsing
    - clarification for missing or optional fields
    - persistent task memory (via context_state)
    - conversational fallback
    """
    try:
        client = get_client()

        # 🧠 Load or create user conversation
        conversation, _ = Conversation.objects.get_or_create(
            organization=user.organization,
            user=user,
            defaults={"title": "Chat Session"},
        )
        context_state = conversation.context_state or {}

        # 💬 Load last few messages for short-term memory
        messages = list(
            Message.objects.filter(conversation=conversation)
            .order_by("-timestamp")[:6]
        )[::-1]
        recent_context = "\n".join(
            f"{'User' if m.sender == 'user' else 'Harvey'}: {m.message_text}"
            for m in messages
        )

        # 🧩 Step 1 — Parse intent, merging any existing field context
        existing_fields = context_state.get("pending_intent", {}).get("fields", {})
        intent_obj = parse_intent(prompt, context_fields=existing_fields)

        # 🔁 Step 2 — Continue existing task if in progress
        if context_state.get("pending_intent"):
            pending = context_state["pending_intent"]
            if intent_obj.get("intent") == "unknown":
                intent_obj = parse_intent(prompt, context_fields=pending["fields"])

        # 🚀 Step 3 — Handle valid intents
        if intent_obj and intent_obj.get("intent") != "unknown":
            intent_name = intent_obj["intent"]

            # Ask for missing or optional info
            if intent_obj.get("clarification"):
                context_state["pending_intent"] = intent_obj
                conversation.context_state = context_state
                conversation.save(update_fields=["context_state", "updated_at"])

                return LLMResponse(
                    response=intent_obj["clarification"],
                    intent=intent_name,
                    success=False,
                )

            # ✅ Execute fully specified intent
            result: ActionResult = execute_action(
                intent=intent_name, payload=intent_obj, user=user
            )

            # Clear pending intent
            context_state.pop("pending_intent", None)
            conversation.context_state = context_state
            conversation.save(update_fields=["context_state", "updated_at"])

            return LLMResponse(
                response=result.message,
                intent=intent_name,
                success=result.ok,
            )

        # 🧹 Step 4 — Reset if new topic
        if context_refresher(prompt):
            context_state.pop("pending_intent", None)
            conversation.context_state = context_state
            conversation.save(update_fields=["context_state", "updated_at"])

        # 💬 Step 5 — Normal chat fallback
        system_prompt = (
            "You are Harvey, a smart HR assistant. "
            "Respond naturally and help with HR tasks like job postings, emails, or interviews."
        )
        full_prompt = f"{system_prompt}\n\nRecent Conversation:\n{recent_context}\n\nUser: {prompt}\nHarvey:"
        resp = client.models.generate_content(model="gemini-2.5-flash", contents=full_prompt)

        return LLMResponse(
            response=(resp.text or "I'm not sure I understood that.").strip(),
            intent=None,
        )

    except Exception as e:
        print("⚠️ LLM Error:", e)
        return LLMResponse(response=f"⚠️ Error generating reply: {e}", success=False)


def context_refresher(prompt: str) -> bool:
    """Detect new topics to reset context."""
    reset_keywords = [
        "create job",
        "add candidate",
        "schedule interview",
        "send email",
        "shortlist",
    ]
    return any(kw in prompt.lower() for kw in reset_keywords)
