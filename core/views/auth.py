from django.shortcuts import render, redirect, reverse
from django.contrib.auth import authenticate, login
from django.contrib.auth.views import LogoutView
from django.contrib import messages
from django.conf import settings
import requests
import os
from core.models.organization import User
from core.models.invite import Invite

# --- Standard Auth ---

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

            # Remember Me Logic
            if request.POST.get('remember-me'):
                request.session.set_expiry(1209600)  # 2 weeks
            else:
                request.session.set_expiry(0)  # Expires on browser close

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

class CustomLogoutView(LogoutView):
    """Allow GET requests for logout (useful for admin links)."""

    def get(self, request, *args, **kwargs):
        request.session.pop("harvey_memory", None)
        return self.post(request, *args, **kwargs)


# --- Google Auth ---

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

    # --- HANDLE ORG INTEGRATION FLOW ---
    if request.session.pop("is_org_integration", False):
        if not request.user.is_authenticated or not request.user.is_org_admin():
            messages.error(request, "Session expired or access denied.")
            return redirect("login")
            
        if not refresh_token:
            messages.warning(request, "Did not receive a Refresh Token. You must revoke access and try again to get offline access.")
            return redirect("org_settings")
            
        # Encrypt and Store
        from core.utils.encryption import encrypt_token
        
        org = request.user.organization
        org.google_refresh_token = encrypt_token(refresh_token)
        org.google_connected_email = email
        # We could also store expires_in if needed, but refresh token is long-lived
        org.save()
        
        messages.success(request, f"Successfully connected Google Workspace for {org.name} as {email}!")
        return redirect("org_settings")
    # -----------------------------------

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


def org_google_login(request):
    """Initiates Google OAuth flow for Org Integration (Gmail + Calendar)."""
    if not request.user.is_authenticated or not request.user.is_org_admin():
        messages.error(request, "Access denied.")
        return redirect("login")

    client_id = os.environ.get("GOOGLE_CLIENT_ID")
    redirect_uri = request.build_absolute_uri(reverse("google_callback"))
    
    # Request extended scopes for sending emails and managing calendar
    scope = "email profile https://www.googleapis.com/auth/gmail.send https://www.googleapis.com/auth/calendar"
    
    if not client_id:
        messages.error(request, "Google OAuth not configured.")
        return redirect("org_settings")

    # Set state in session to know this is an integration flow, not a login flow
    request.session["is_org_integration"] = True
    
    auth_url = f"{GOOGLE_AUTH_URL}?client_id={client_id}&redirect_uri={redirect_uri}&response_type=code&scope={scope}&access_type=offline&prompt=consent"
    return redirect(auth_url)
