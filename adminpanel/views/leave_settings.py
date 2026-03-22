from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone
from core.models.leaves import LeaveSystemConfig, OrganizationLeavePolicy
from .utils import is_org_admin

@login_required
@user_passes_test(is_org_admin)
def leave_settings(request):
    """View to manage yearly leave allocations via a token-protected area."""
    org = request.user.organization
    if not request.user.is_org_admin():
        messages.error(request, "Access Denied: Leave Management is restricted to Organization Admins only.")
        return redirect('admin_dashboard')
        
    config, created = LeaveSystemConfig.objects.get_or_create(organization=org)
    
    if request.method == "POST":
        action = request.POST.get("action")
        
        if action == "unlock_leave_config":
            edit_token = request.POST.get("edit_token")
            
            if not config.edit_token or edit_token != config.edit_token:
                messages.error(request, "Invalid Authorization Token. Configuration unlocking failed.")
                return redirect('leave_settings')
                
            if config.edit_token_expires_at and timezone.now() > config.edit_token_expires_at:
                messages.error(request, "Edit Token expired. Please generate a new one from the Admin portal.")
                return redirect('leave_settings')
                
            request.session['leave_config_unlocked'] = True
            messages.success(request, "Configuration unlocked for editing.")
            return redirect('leave_settings')

        elif action == "lock_leave_config":
            config.edit_token = None
            config.edit_token_expires_at = None
            config.save()
            request.session.pop('leave_config_unlocked', None)
            messages.success(request, "Configuration locked successfully. You will need a new token to edit again.")
            return redirect('leave_settings')

        elif action == "add_policy":
            if not request.session.get('leave_config_unlocked'):
                messages.error(request, "Session expired or configuration not unlocked.")
                return redirect('leave_settings')
                
            year = request.POST.get("year")
            leave_type = request.POST.get("leave_type")
            default_allocated = request.POST.get("default_allocated")
            
            if not year or not leave_type or not default_allocated:
                messages.error(request, "All fields are required.")
                return redirect('leave_settings')
                
            OrganizationLeavePolicy.objects.update_or_create(
                organization=org,
                year=int(year),
                leave_type=leave_type,
                defaults={'default_allocated': float(default_allocated)}
            )
            messages.success(request, f"Leave Policy for {leave_type} in {year} saved successfully.")
            return redirect('leave_settings')

        elif action == "delete_policy":
            if not request.session.get('leave_config_unlocked'):
                messages.error(request, "Session expired or configuration not unlocked.")
                return redirect('leave_settings')
                
            policy_id = request.POST.get("policy_id")
            policy = get_object_or_404(OrganizationLeavePolicy, id=policy_id, organization=org)
            
            # Optionally check if deleting leaves active balances exposed?
            # It's okay, leave balances are snapshots at creation time for the employees.
            policy.delete()
            messages.success(request, "Leave Policy removed successfully.")
            return redirect('leave_settings')

    is_unlocked = request.session.get('leave_config_unlocked', False)
    policies = OrganizationLeavePolicy.objects.filter(organization=org).order_by('-year', 'leave_type')
    
    return render(request, 'leaves/leave_settings.html', {
        'is_unlocked': is_unlocked,
        'policies': policies
    })
