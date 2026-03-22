from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from core.models.organization import User
from .utils import is_org_admin, is_admin_manager_hr

@login_required
@user_passes_test(is_admin_manager_hr)
def admin_dashboard(request):
    """Admin dashboard with user and chatbot management."""
    org = request.user.organization
    
    total_users = User.objects.filter(organization=org).count()
    admin_users = User.objects.filter(organization=org, role="org_admin").count()
    staff_users = User.objects.filter(organization=org, is_staff=True).count()
    regular_users = User.objects.filter(organization=org, is_staff=False).count()

    def get_pct(count):
        val = (count / total_users * 100) if total_users > 0 else 0
        return int(round(val))

    from core.models.leaves import LeaveRequest
    pending_leaves = LeaveRequest.objects.filter(status='pending', organization=org).count()
    
    # Check for Anniversary Popup (if today is their join date anniversary)
    import datetime
    today = datetime.datetime.now()
    # Simple check: month and day match (but not the exact same year to avoid popup on day 1 if we only want anniversaries)
    show_anniversary_popup = False
    if request.user.date_joined:
        join_date = request.user.date_joined
        if join_date.month == today.month and join_date.day == today.day and join_date.year < today.year:
            show_anniversary_popup = True

    context = {
        "org_name": org.name if org else "No Organization",
        "total_users": total_users,
        "admin_users": admin_users,
        "staff_users": staff_users,
        "regular_users": regular_users,
        "admin_pct": get_pct(admin_users),
        "staff_pct": get_pct(staff_users),
        "regular_pct": get_pct(regular_users),
        "pending_leaves": pending_leaves,
        "show_anniversary_popup": show_anniversary_popup,
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
