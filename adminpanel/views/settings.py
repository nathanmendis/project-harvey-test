from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from .utils import is_org_admin

@login_required
@user_passes_test(is_org_admin)
def org_settings(request):
    """View to manage organization settings and integrations."""
    org = request.user.organization
    
    if request.method == "POST":
        action = request.POST.get("action")
        
        if action == "update_profile":
            org.name = request.POST.get("name")
            org.domain = request.POST.get("domain")
            org.save()
            messages.success(request, "Organization profile updated.")
            return redirect('org_settings')
            
        elif action == "disconnect_google":
            # Clear encrypted credentials
            org.google_refresh_token = None
            org.google_token_expires = None
            org.google_connected_email = None
            org.save()
            messages.info(request, "Google Workspace disconnected. You can no longer send automated emails.")
            return redirect('org_settings')

    # Check connection status (simple check if token exists)
    is_connected = bool(org.google_refresh_token)
    connected_email = org.google_connected_email if org.google_connected_email else "Connected Account"
    
    return render(request, 'org_settings.html', {
        'org': org,
        'is_connected': is_connected,
        'connected_email': connected_email
    })
