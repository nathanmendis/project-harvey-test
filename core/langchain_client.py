# core/langchain_client.py
from django.conf import settings
from langchain_google_genai import ChatGoogleGenerativeAI

def get_langchain_client():
    """Initialize and reuse the LangChain Gemini chat model."""
    return ChatGoogleGenerativeAI(
        model="gemini-1.5-pro",
        temperature=0.3,
        google_api_key=settings.GOOGLE_API_KEY,
    )
