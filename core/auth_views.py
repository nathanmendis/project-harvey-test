from django.shortcuts import redirect, render
from django.conf import settings
from django.contrib.auth import login
from django.contrib import messages
from django.urls import reverse
import requests
from core.models.organization import User
from core.models.invite import Invite
from django.utils import timezone
import os

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USER_INFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

def google_login(request):
    """Initiates the Google OAuth flow."""
    invite_token = request.GET.get("invite")
    if invite_token:
        request.session["invite_token"] = invite_token
    
    # Use environment variables or settings for credentials
    client_id = os.environ.get("GOOGLE_CLIENT_ID")
    redirect_uri = request.build_absolute_uri(reverse("google_callback"))
    
    # Only request basic identity scopes (Email + Profile)
    # We use the System Token for sending emails, so users don't need to grant Gmail access.
    scope = "email profile"
    
    if not client_id:
        messages.error(request, "Google OAuth not configured (Missing Client ID).")
        return redirect("login")

    # Force consent to ensure we get a refresh token
    auth_url = f"{GOOGLE_AUTH_URL}?client_id={client_id}&redirect_uri={redirect_uri}&response_type=code&scope={scope}&access_type=offline&prompt=consent"
    return redirect(auth_url)

def google_callback(request):
    """Handles the callback from Google."""
    code = request.GET.get("code")
    
    if not code:
        messages.error(request, "Authentication failed (No code returned).")
        return redirect("login")

    client_id = os.environ.get("GOOGLE_CLIENT_ID")
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")
    redirect_uri = request.build_absolute_uri(reverse("google_callback"))

    # Exchange code for token
    token_data = {
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }
    
    response = requests.post(GOOGLE_TOKEN_URL, data=token_data)
    if response.status_code != 200:
        messages.error(request, "Failed to get token from Google.")
        return redirect("login")
    
    tokens = response.json()
    access_token = tokens.get("access_token")
    refresh_token = tokens.get("refresh_token") # Only present if prompt=consent
    expires_in = tokens.get("expires_in")
    
    # Get user info
    user_info_response = requests.get(GOOGLE_USER_INFO_URL, headers={"Authorization": f"Bearer {access_token}"})
    if user_info_response.status_code != 200:
        messages.error(request, "Failed to fetch user info.")
        return redirect("login")
        
    user_data = user_info_response.json()
    email = user_data.get("email")
    
    if not email:
        messages.error(request, "No email provided by Google.")
        return redirect("login")

    # 1. Try to find existing user
    user = User.objects.filter(email=email).first()
    
    if user:
        # User exists -> Login
        login(request, user)
        return redirect(settings.LOGIN_REDIRECT_URL)
    
    # 2. Check for Invite
    # Check session for explicit token first
    invite_token = request.session.pop("invite_token", None)
    invite = None
    
    if invite_token:
        invite = Invite.objects.filter(token=invite_token, email=email).first()
    
    # If no token in session or mismatch, try finding by email alone
    if not invite:
        invite = Invite.objects.filter(email=email).first()
        
    if invite and invite.is_valid():
        # Valid invite found -> Create User
        username = email.split("@")[0]
        # Ensure unique username
        base_username = username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1
            
        new_user = User.objects.create_user(
            username=username,
            email=email,
            password=None, #/ unusable password
            role=invite.role,
            organization=invite.organization,
            name=user_data.get("name", "")
        )
            
        new_user.has_chat_access = True 
        new_user.save()
        
        invite.accepted = True
        invite.save()
        
        login(request, new_user)
        messages.success(request, f"Welcome to {invite.organization.name}!")
        return redirect(settings.LOGIN_REDIRECT_URL)
    
    # 3. No User, No Invite -> Block
    return render(request, "core/no_access.html", {"message": "Access Restricted: You need an invitation to join."})
