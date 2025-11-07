# core/consumers.py
import json
import os
import django
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
from .llm_engine import generate_llm_reply

if not django.conf.settings.configured:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project_harvey.settings")
    django.setup()


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        from .models import Conversation  # Lazy import

        self.user = self.scope["user"]
        if not self.user.is_authenticated:
            await self.close()
            return

        # ✅ Access the user's organization safely
        organization = await sync_to_async(lambda: self.user.organization)()

        # ✅ Get or create a conversation (in a thread-safe way)
        conversation, _ = await sync_to_async(Conversation.objects.get_or_create)(
            organization=organization,
            user=self.user,
            defaults={"title": "Chat Session"},
        )
        self.conversation = conversation

        await self.accept()

    async def receive(self, text_data):
        from .models import Message

        data = json.loads(text_data)
        prompt = data.get("prompt", "").strip()
        if not prompt:
            await self.send(text_data=json.dumps({
                "response": "Please type something."
            }))
            return

        organization = await sync_to_async(lambda: self.user.organization)()

        # ✅ Save user message
        await sync_to_async(Message.objects.create)(
            organization=organization,
            conversation=self.conversation,
            sender="user",
            message_text=prompt,
        )

        # Send immediate feedback
        await self.send(text_data=json.dumps({"response": "Thinking..."}))

        # ✅ Generate LLM reply
        llm_response = await sync_to_async(generate_llm_reply)(prompt, user=self.user)

        # ✅ Save AI reply
        await sync_to_async(Message.objects.create)(
            organization=organization,
            conversation=self.conversation,
            sender="ai",
            message_text=llm_response.response,
        )

        # ✅ Send response to client
        await self.send(text_data=json.dumps({
            "response": llm_response.response
        }))
