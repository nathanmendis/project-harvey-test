import os
import django
import json

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project_harvey.settings')
django.setup()

from core.models.organization import Organization, User
from core.models.recruitment import Candidate, JobRole, CandidateJobScore
from core.ai.agentic.graph.graph import graph
from langchain_core.messages import HumanMessage

def run_actual_demo():
    print("--- Setting up Data ---")
    # Get or create org and user
    org, _ = Organization.objects.get_or_create(name="Real Demo Org", domain="demo.com")
    user, _ = User.objects.get_or_create(
        username="demo_hr_user", 
        defaults={"organization": org, "role": "hr"}
    )
    if not user.organization:
        user.organization = org
        user.save()
    
    # Create a Job Role with rich data for the LLM to analyze
    job, created = JobRole.objects.update_or_create(
        organization=org,
        title="Senior Python Developer",
        defaults={
            "description": "We need a backend developer with 5+ years of experience in Python, Django, and LangChain.",
            "requirements": "Proficient in Python, PostgreSQL, LangChain, and Agentic workflows. Remote OK.",
            "department": "Engineering"
        }
    )

    # Refresh candidates
    Candidate.objects.filter(organization=org).delete()
    
    c1 = Candidate.objects.create(
        organization=org,
        name="John Python Expert",
        email="john@expert.com",
        skills=["Python", "Django", "Postgres", "LangChain"],
        parsed_data="John has 10 years of experience in Python and has built multiple AI agents using LangChain. He is an expert in Django.",
        status="pending"
    )
    
    c2 = Candidate.objects.create(
        organization=org,
        name="Jane React Junior",
        email="jane@frontend.com",
        skills=["React", "CSS", "HTML"],
        parsed_data="Jane is a recent boot camp graduate specializing in React and frontend styling. She has no backend experience.",
        status="pending"
    )

    print(f"Data ready. Job ID: {job.id}. Candidates: {c1.name}, {c2.name}")

    print("\n--- Invoking Agent with Real LLM and Tool ---")
    query = f"Can you shortlist the candidates for our '{job.title}' role (ID: {job.id})? Please give me the match scores and your reasoning."
    
    state_input = {
        "messages": [HumanMessage(content=query)],
        "user_id": user.id,
        "context": {}
    }
    
    # Run the graph
    print("Agent is thinking and calling tools...")
    result = graph.invoke(state_input, config={"configurable": {"thread_id": "demo_thread_final"}})
    
    print("\n--- Conversation History (LLM + Tool Interactions) ---")
    for msg in result["messages"]:
        if isinstance(msg, HumanMessage):
            print(f"\n[User]: {msg.content}")
        elif hasattr(msg, 'tool_calls') and msg.tool_calls:
            print(f"\n[Harvey AI Agent]: (Thinking... Calling tool '{msg.tool_calls[0]['name']}')")
            print(f"Arguments: {json.dumps(msg.tool_calls[0]['args'], indent=2)}")
        elif msg.type == "tool":
            print(f"\n[Tool Output]:")
            try:
                data = json.loads(msg.content)
                print(json.dumps(data, indent=2))
            except:
                print(msg.content)
        else:
            print(f"\n[Harvey AI Response]:\n{msg.content}")

if __name__ == "__main__":
    run_actual_demo()
