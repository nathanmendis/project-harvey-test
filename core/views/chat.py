from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
import json
from core.llm_graph.chat_service import generate_llm_reply

@login_required
def chat_page(request):
    """Render the chat UI if user has access."""
    if not getattr(request.user, "has_chat_access", False):
        return render(request, "core/no_access.html")  # access blocked
    return render(request, "core/core.html")

@csrf_exempt
@require_POST
@login_required
def chat_with_llm(request):
    """Handle user input and return LLM response (JSON)."""
    if not getattr(request.user, "has_chat_access", False):
        return JsonResponse({"error": "Access denied"}, status=403)

    try:
        data = json.loads(request.body)
        prompt = data.get("prompt", "").strip()

        if not prompt:
            return JsonResponse({"error": "Prompt missing"}, status=400)

        #  Pass user context into the LLM function
        response = generate_llm_reply(prompt, user=request.user, request=request)

        return JsonResponse({"response": response.response})

    except Exception as e:
        print(f"⚠️ Chat API Error: {e}")
        return JsonResponse({"error": str(e)}, status=500)
