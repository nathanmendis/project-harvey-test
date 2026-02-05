
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

def run_final_tests():
    print("🚀 Starting Final System Verification (Project Harvey v3.0)")
    
    # Get a test user and organization
    org = Organization.objects.first()
    user = User.objects.filter(organization=org).first()
    
    if not user:
        print("❌ No test user found. Please ensure seed data exists.")
        return

    test_queries = [
        "hi",                               # Test Greeting (Router -> Chat)
        "who is steve?",                     # Test Candidate Search (Router -> Tool -> Template)
        "what is the attendance policy?"      # Test Policy Search (Router -> Tool -> Llama NLP)
    ]
    
    convo_id = None
    
    for query in test_queries:
        print(f"\n💬 USER: {query}")
        print("-" * 50)
        
        try:
            result = generate_llm_reply(query, user, conversation_id=convo_id)
            convo_id = result.conversation_id
            print(f"🤖 HARVEY: {result.response}")
        except Exception as e:
            print(f"❌ ERROR: {e}")
        
        print("-" * 50)

if __name__ == "__main__":
    run_final_tests()
