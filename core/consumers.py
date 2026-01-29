import json
import os
import django
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
from .llm_graph.chat_service import generate_llm_reply


if not django.conf.settings.configured:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project_harvey.settings")
    django.setup()


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        if not self.user.is_authenticated:
            await self.close()
            return

        # No longer locking to a single conversation on connect
        await self.accept()

    async def receive(self, text_data):
        data = json.loads(text_data)
        prompt = data.get("prompt", "").strip()
        conversation_id = data.get("conversation_id") # May be None for new chat

        if not prompt:
            await self.send(text_data=json.dumps({
                "response": "Please type something."
            }))
            return

        await self.send(text_data=json.dumps({"response": "Thinking..."}))
 
        # Generate the LLM reply via service
        # Service handles DB saving for both User/AI messages now
        llm_response = await sync_to_async(generate_llm_reply)(
            prompt,
            user=self.user,
            conversation_id=conversation_id
        )

        # Send back response + metadata (id/title) so frontend can lock context
        await self.send(text_data=json.dumps({
            "response": llm_response.response,
            "conversation_id": llm_response.conversation_id,
            "title": llm_response.title
        }))
