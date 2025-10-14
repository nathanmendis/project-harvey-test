# core/views.py
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import json
from .llm_engine import generate_llm_reply
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.contrib.auth.decorators import login_required

@login_required  
def chat_page(request):
    """Render the chat UI page."""
    return render(request, "core/core.html")


@csrf_exempt
@require_POST
def chat_with_llm(request):
    """Handle user input and return LLM response."""
    try:
        data = json.loads(request.body)
        prompt = data.get("prompt", "").strip()
        if not prompt:
            return JsonResponse({"error": "Prompt missing"}, status=400)

        response = generate_llm_reply(prompt)
        return JsonResponse({"response": response.response})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)



def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')  # Redirect if already logged in

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('chat_view')  # Change to your dashboard/home route
        else:
            messages.error(request, 'Invalid username or password.')

    return render(request, 'core/login_page.html')
