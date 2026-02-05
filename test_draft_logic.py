
import os
import django
import json
import asyncio
from uuid import uuid4

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project_harvey.settings')
django.setup()

from core.llm_graph.chat_service import generate_llm_reply
from core.models.organization import Organization
from core.models.chatbot import User

def run_draft_tests():
    print("🚀 Verifying Email Draft & Send Logic (Project Harvey v3.0)")
    
    # Get a test user
    org = Organization.objects.first()
    user = User.objects.filter(organization=org).first()
    
    if not user:
        print("❌ No test user found.")
        return

    test_queries = [
        "draft an email to nathanmendis17@gmail.com saying thanks", # Test 1: Draft only (should be CHAT)
        "send email to nathanmendis17@gmail.com saying hi",        # Test 2: Send only (should be TOOL)
        "send email to nathanmendis17@gmail.com saying it is a test email but also draft the email" # Test 3: Draft + Send (should be TOOL with draft)
    ]
    
    for query in test_queries:
        print(f"\n💬 USER: {query}")
        print("-" * 50)
        
        try:
            result = generate_llm_reply(query, user)
            print(f"🤖 HARVEY: {result.response}")
        except Exception as e:
            print(f"❌ ERROR: {e}")
        
        print("-" * 50)

if __name__ == "__main__":
    run_draft_tests()
