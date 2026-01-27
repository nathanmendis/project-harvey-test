import os
import django
import sys

# Setup Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project_harvey.settings')
django.setup()

from core.llm_graph.nodes import harvey_node
from core.models.organization import User, Organization
from langchain_core.messages import HumanMessage, AIMessage

def test_add_candidate_hallucination():
    print("Testing Anti-Hallucination for Add Candidate...")
    
    # Setup User
    org, _ = Organization.objects.get_or_create(name="Test Org")
    user, _ = User.objects.get_or_create(username="test_hallucination", organization=org)
    
    # Simulate State
    state = {
        "messages": [
            HumanMessage(content="add candidate John Doe"),
            AIMessage(content="I'll need his email, phone, and skills."),
            HumanMessage(content="his email is jhon@gmial.com phone number is 283491458915 skills are python, django, MK")
        ],
        "user_id": user.id,
        "context": {},
        "trace": []
    }
    
    # Run Node
    result = harvey_node(state)
    
    # Check Result
    messages = result.get("messages", [])
    pending_tool = result.get("pending_tool")
    
    if pending_tool:
        print(f"✅ SUCCESS: Tool call generated: {pending_tool['name']}")
        print(f"Args: {pending_tool['args']}")
        if pending_tool['name'] == 'add_candidate':
            print("Correct tool selected.")
        else:
            print("❌ WRONG TOOL selected.")
    else:
        print("❌ FAILURE: No tool call generated. Agent hallucinated or refused.")
        print("Response:", messages[0].content if messages else "No response")

if __name__ == "__main__":
    test_add_candidate_hallucination()
