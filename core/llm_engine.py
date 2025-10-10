# core/llm_engine.py
from gpt4all import GPT4All
from pydantic import BaseModel
import os

# Define the model path relative to the project directory.
# This makes it easy to manage where your models are stored.
MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "llm_models")

# Define the name of the model file.
# The `GPT4All` library will look for this specific file.
# Note: The model name from your file system is `mistral-7b-instruct-v0.1.Q4_0.gguf`.
MODEL_NAME = "mistral-7b-instruct-v0.1.Q4_0.gguf"

# Load the model once at startup to avoid reloading it for every request.
# The `model_name` parameter is now correctly set.
# The `allow_download` is set to `False` to prevent unexpected downloads if the model is not found.
try:
    model = GPT4All(model_name=MODEL_NAME, model_path=MODEL_PATH, allow_download=False)
except Exception as e:
    # A robust error handling message for when the model file is not found.
    print(f"Error loading GPT4All model: {e}")
    print(f"Please ensure the model file '{MODEL_NAME}' is located in the '{MODEL_PATH}' directory.")
    model = None

class LLMResponse(BaseModel):
    response: str

def generate_llm_reply(prompt: str) -> LLMResponse:
    """Generate a response from a local GGUF model."""
    if not model:
        return LLMResponse(response="Sorry, the AI model is not available at the moment.")

    system_prompt = (
        "You are Harvey, an AI HR assistant that helps with resumes, emails, and leaves."
    )

    full_prompt = f"{system_prompt}\nUser: {prompt}\nHarvey:"
    reply = model.generate(full_prompt, max_tokens=300, temp=0.7)
    return LLMResponse(response=reply.strip())

from django.shortcuts import render
from django.http import JsonResponse
from .llm_engine import generate_llm_reply

def chat_with_llm(request):
    """
    Handles the chat interface. This view can be used for both
    displaying the chat page and handling AJAX requests.
    """
    if request.method == "POST":
        # This is where you would process the user's message
        user_message = request.POST.get('message', '')
        if user_message:
            ai_response = generate_llm_reply(user_message).response
            # In a full app, you would also save this message to your database
            return JsonResponse({'response': ai_response})
        return JsonResponse({'error': 'No message provided'}, status=400)

    # This will render the chat template for a GET request
    return render(request, 'chat_core/chat.html')