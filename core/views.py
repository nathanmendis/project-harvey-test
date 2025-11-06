from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.contrib.auth.decorators import login_required
import json

from django.contrib.auth.views import LogoutView

from .llm_engine import generate_llm_reply
from .models import User  # Import your custom User model


# LOGIN VIEW (for all users)

def login_view(request):
    
    if request.user.is_authenticated:
        # Already logged in: redirect by role
        if request.user.role == "org_admin" or request.user.is_superuser:
            return redirect('admin_dashboard')
        elif getattr(request.user, "has_chat_access", False):
            return redirect('chat_view')
        else:
            return render(request, 'core/no_access.html')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)

            # Redirect based on role or permissions
            if user.role == "org_admin" or user.is_superuser:
                return redirect('admin_dashboard')
            elif getattr(user, "has_chat_access", False):
                return redirect('chat_view')
            else:
                return render(request, 'core/no_access.html')
        else:
            messages.error(request, 'Invalid username or password.')

    return render(request, 'core/login_page.html')

# CHAT PAGE

@login_required
def chat_page(request):
    """Render the chat UI if user has access."""
    if not getattr(request.user, "has_chat_access", False):
        return render(request, "core/no_access.html")  # access blocked
    return render(request, "core/core.html")



# CHAT API ENDPOINT

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

        response = generate_llm_reply(prompt)
        return JsonResponse({"response": response.response})

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


class CustomLogoutView(LogoutView):
    """Allow GET requests for logout (useful for admin links)."""
    def get(self, request, *args, **kwargs):
        return self.post(request, *args, **kwargs)