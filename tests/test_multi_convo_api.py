
import os
import django
from django.conf import settings
from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from core.models import Conversation, Message, Organization
from core.api import list_conversations, get_conversation_messages
import json

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project_harvey.settings")
django.setup()

User = get_user_model()

class MultipleConversationsTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.org = Organization.objects.create(name="Test Org")
        self.user = User.objects.create_user(username="test_multi", password="password", organization=self.org)
        
        # Create Conversations
        self.c1 = Conversation.objects.create(user=self.user, organization=self.org, title="Chat 1")
        self.c2 = Conversation.objects.create(user=self.user, organization=self.org, title="Chat 2")
        
        # Add messages to C1
        for i in range(30):
            Message.objects.create(conversation=self.c1, organization=self.org, sender="user", message_text=f"Msg {i}")

    def test_list_conversations(self):
        request = self.factory.get('/api/conversations/')
        request.user = self.user
        
        response = list_conversations(request)
        data = json.loads(response.content)
        
        print(f"\nList Conversations: Found {len(data['conversations'])}")
        self.assertEqual(len(data['conversations']), 2)
        self.assertEqual(data['conversations'][0]['title'], "Chat 2") # Recent first (created later)

    def test_pagination(self):
        # Fetch latest 20
        request = self.factory.get(f'/api/conversations/{self.c1.id}/messages/?limit=20&offset=0')
        request.user = self.user
        response = get_conversation_messages(request, self.c1.id)
        data = json.loads(response.content)
        
        print(f"Pagination Page 1: Got {len(data['messages'])} messages. Has More: {data['has_more']}")
        self.assertEqual(len(data['messages']), 20)
        self.assertTrue(data['has_more'])
        self.assertEqual(data['messages'][0]['text'], "Msg 10") # Oldest in this slice (since reversed for display: 10..29)
        # Wait, slices are delicate. 
        # API logic: order_by('-timestamp')[offset : offset+limit] => 29, 28... 10
        # Then reversed => 10, 11... 29.
        # So last message in list should be "Msg 29".
        self.assertEqual(data['messages'][-1]['text'], "Msg 29")

        # Fetch older 10
        request = self.factory.get(f'/api/conversations/{self.c1.id}/messages/?limit=20&offset=20')
        request.user = self.user
        response = get_conversation_messages(request, self.c1.id)
        data = json.loads(response.content)
        
        print(f"Pagination Page 2: Got {len(data['messages'])} messages. Has More: {data['has_more']}")
        self.assertEqual(len(data['messages']), 10) # 0..9 left
        self.assertFalse(data['has_more'])
        self.assertEqual(data['messages'][0]['text'], "Msg 0")
