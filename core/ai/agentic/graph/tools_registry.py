import os
from dotenv import load_dotenv
load_dotenv()
from langchain_google_genai import ChatGoogleGenerativeAI
from core.ai.agentic.tools.recruitment_tools import (
    add_candidate,
    add_candidate_with_resume,
    schedule_interview,
    create_job_description,
    shortlist_candidates
)
from core.ai.rag.tools.search_tool import search_knowledge_base
from core.ai.rag.tools.policy_search_tool import search_policies
from core.ai.agentic.tools.email_tool import send_email_tool
from core.ai.agentic.tools.calendar_tool import create_calendar_event_tool

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

def get_router_llm():
    """Small, fast model for intent classification"""
    groq_key = os.getenv("GROQ_API_KEY")
    if not groq_key: 
        raise ValueError("GROQ_API_KEY not set")
        
    return ChatGroq(
        model="llama-3.1-8b-instant",
        temperature=0.0,
        api_key=groq_key
    )

def get_reasoner_llm():
    """Llama 4 Scout: specialized 2026-gen model for agentic reasoning and tool use"""
    groq_key = os.getenv("GROQ_API_KEY")
    if not groq_key:
         raise ValueError("GROQ_API_KEY not set")

    return ChatGroq(
        model="meta-llama/llama-4-scout-17b-16e-instruct",
        temperature=0.0,
        api_key=groq_key
    )

def get_lite_llm():
    """Fast model for simple NLP normalization and rephrasing"""
    groq_key = os.getenv("GROQ_API_KEY")
    if not groq_key:
         raise ValueError("GROQ_API_KEY not set")

    return ChatGroq(
        model="llama-3.1-8b-instant",
        temperature=0.1,
        api_key=groq_key
    )
