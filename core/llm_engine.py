from pydantic import BaseModel
from google import genai
from dotenv import load_dotenv


load_dotenv()
client = genai.Client()

class LLMResponse(BaseModel):
    response: str

def generate_llm_reply(prompt: str) -> LLMResponse:
    """Generate a response using Google Gemini API."""
    try:
        system_prompt = (
            "You are Harvey, an AI HR assistant that helps with resumes, emails, and leaves."
        )
        full_prompt = f"{system_prompt}\nUser: {prompt}\nHarvey:"

        response =client.models.generate_content(
            model="gemini-2.5-flash",
            contents=full_prompt,
            )


        return LLMResponse(response=response.text.strip())

    except Exception as e:
        return LLMResponse(response=f"Error generating reply: {e}")
