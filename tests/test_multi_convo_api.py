import json
from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from core.models import Conversation, Message, Organization
from core.api import list_conversations, get_conversation_messages

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
        
        self.assertEqual(len(data['conversations']), 2)
        # Assuming ordering is -timestamp or similar
        self.assertEqual(data['conversations'][0]['title'], "Chat 2") 

    def test_pagination(self):
        # Fetch latest 20
        request = self.factory.get(f'/api/conversations/{self.c1.id}/messages/?limit=20&offset=0')
        request.user = self.user
        response = get_conversation_messages(request, self.c1.id)
        data = json.loads(response.content)
        
        self.assertEqual(len(data['messages']), 20)
        self.assertTrue(data['has_more'])
        self.assertEqual(data['messages'][-1]['text'], "Msg 29")

        # Fetch older 10
        request = self.factory.get(f'/api/conversations/{self.c1.id}/messages/?limit=20&offset=20')
        request.user = self.user
        response = get_conversation_messages(request, self.c1.id)
        data = json.loads(response.content)
        
        self.assertEqual(len(data['messages']), 10) 
        self.assertFalse(data['has_more'])
        self.assertEqual(data['messages'][0]['text'], "Msg 0")
