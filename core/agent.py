from langchain_classic.chains import LLMChain
from langchain_classic.memory import ConversationBufferMemory
from langchain_community.chat_message_histories import RedisChatMessageHistory
from langchain_classic.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_classic.tools import StructuredTool
from langchain_core.language_models import LLM
from typing import List, Optional
import os
import google.generativeai as genai
from .actions import execute_action, ActionResult


# --- Gemini Wrapper ---

class GeminiLLM(LLM):
    model: str = "gemini-2.5-flash"
    temperature: float = 0.3

    def _call(self, prompt: str, stop: Optional[List[str]] = None) -> str:
        try:
            model = genai.GenerativeModel(self.model)
            response = model.generate_content(prompt)

            # Extract usable text safely
            if hasattr(response, "text") and response.text:
                return response.text.strip()

            if hasattr(response, "candidates") and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, "content") and candidate.content.parts:
                    part = candidate.content.parts[0]
                    if hasattr(part, "text"):
                        return part.text.strip()

            return "⚠️ Gemini returned no usable response."
        except Exception as e:
            return f"⚠️ Gemini API error: {e}"

    @property
    def _llm_type(self):
        return "gemini_custom"


genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))


# --- Agent Factory ---

def get_harvey_agent(user=None, request=None):
    """Creates a Gemini-powered HR agent with Redis + LangChain memory."""

    llm = GeminiLLM()
    session_id = f"user:{user.id}:session"

    # Persistent chat history via Redis
    redis_chat = RedisChatMessageHistory(
        url="redis://127.0.0.1:6379/1",
        session_id=session_id
    )

    # Conversation buffer wraps Redis history
    memory = ConversationBufferMemory(
        memory_key="chat_history",
        chat_memory=redis_chat,
        return_messages=True,
    )

    # Define tools (like email, job posting, etc.)
    def execute_hr_action(intent: str, payload: dict) -> str:
        try:
            result: ActionResult = execute_action(intent=intent, payload=payload, user=user)
            return result.message
        except Exception as e:
            return f"⚠️ Error executing action: {e}"

    tools = [
        StructuredTool.from_function(
            name="execute_hr_action",
            description="Executes HR tasks (send_email, add_candidate, etc.)",
            func=execute_hr_action,
        )
    ]

    # Unified system prompt (no manual SYSTEM MEMORY injection)
    prompt = ChatPromptTemplate.from_messages([
        ("system",
         "You are Harvey, an intelligent HR assistant for an organization. "
         "You can recall structured memory (like intent and fields) from Redis "
         "and natural conversation history from the chat buffer. "
         "Use both to reason logically about what the user wants."),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}")
    ])

    return LLMChain(llm=llm, prompt=prompt, memory=memory, verbose=True)
