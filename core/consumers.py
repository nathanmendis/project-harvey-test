# core/consumers.py

import json
from channels.generic.websocket import AsyncWebsocketConsumer
from .llm_engine import generate_llm_reply

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()

    async def disconnect(self, close_code):
        pass

    async def receive(self, text_data):
        """Receive message from WebSocket and send LLM reply."""
        text_data_json = json.loads(text_data)
        prompt = text_data_json['prompt']

        # Send "Thinking..." message back to the client
        await self.send(text_data=json.dumps({
            'response': "Thinking..."
        }))
        
        # Call the LLM (this part needs to be synchronous)
        # We'll use sync_to_async to handle this.
        from asgiref.sync import sync_to_async
        llm_response = await sync_to_async(generate_llm_reply)(prompt)
        
        # Send the final LLM response
        await self.send(text_data=json.dumps({
            'response': llm_response.response
        }))