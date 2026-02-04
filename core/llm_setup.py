import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq

load_dotenv()

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
    """Large, powerful model for complex reasoning and drafting"""
    groq_key = os.getenv("GROQ_API_KEY")
    if not groq_key:
         raise ValueError("GROQ_API_KEY not set")

    return ChatGroq(
        model="llama-3.3-70b-versatile",
        temperature=0.0,
        api_key=groq_key
    )
