from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from core.models.organization import User
from .utils import is_org_admin

@login_required
@user_passes_test(is_org_admin)
def admin_dashboard(request):
    """Admin dashboard with user and chatbot management."""
    org = request.user.organization
    
    total_users = User.objects.filter(organization=org).count()
    admin_users = User.objects.filter(organization=org, role="org_admin").count()
    staff_users = User.objects.filter(organization=org, is_staff=True).count()
    regular_users = User.objects.filter(organization=org, is_staff=False).count()

    def get_pct(count):
        return (count / total_users * 100) if total_users > 0 else 0

    context = {
        "org_name": org.name if org else "No Organization",
        "total_users": total_users,
        "admin_users": admin_users,
        "staff_users": staff_users,
        "regular_users": regular_users,
        "admin_pct": get_pct(admin_users),
        "staff_pct": get_pct(staff_users),
        "regular_pct": get_pct(regular_users),
    }

    # Check Google Token Validity (if configured)
    if org and org.google_refresh_token:
        try:
            from integrations.google.gmail import GmailService
            # Attempting to initialize service triggers auth check/refresh
            GmailService(user=request.user) 
        except Exception:
            messages.warning(
                request, 
                "Your Google Workspace connection has expired or is invalid. Please reconnect in Settings."
            )

    return render(request, "dashboard.html", context)
