import os
from dotenv import load_dotenv
load_dotenv()
from langchain_google_genai import ChatGoogleGenerativeAI
from core.tools.base import (
    add_candidate,
    add_candidate_with_resume,
    schedule_interview,
    create_job_description,
    shortlist_candidates
)
from core.tools.search_tool import search_knowledge_base
from core.tools.policy_search_tool import search_policies
from core.tools.email_tool import send_email_tool
from core.tools.calendar_tool import create_calendar_event_tool

AVAILABLE_TOOLS = [
    add_candidate,
    add_candidate_with_resume,
    schedule_interview,
    create_job_description,
    shortlist_candidates,
    search_knowledge_base,
    search_policies,
    send_email_tool,
    create_calendar_event_tool,
]

tool_registry = {t.name: t.func for t in AVAILABLE_TOOLS}



from langchain_groq import ChatGroq

def get_llm():
    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key:
        return ChatGroq(
            model="llama-3.3-70b-versatile",
            temperature=0.0,
            api_key=groq_key
        )

    # Fallback to Gemini
    key = os.getenv("GOOGLE_API_KEY")
    if not key:
        raise RuntimeError("GOOGLE_API_KEY not set")
    return ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        temperature=0.0,
        google_api_key=key,
        max_retries=0
    )
