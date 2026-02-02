from django.shortcuts import render, redirect

def landing_page(request):
    """Render the public landing page."""
    if request.user.is_authenticated:
        # Already logged in: redirect by role
        if request.user.role == "org_admin" or request.user.is_superuser:
            return redirect('admin_dashboard')
        elif getattr(request.user, "has_chat_access", False):
            return redirect('chat_view')
        else:
            return render(request, 'core/no_access.html')  
    return render(request, "core/landing_page.html")
