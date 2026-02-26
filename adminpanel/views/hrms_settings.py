from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone
from core.models.recruitment import HRMSSystemConfig
from integrations.hrms.sync.tracker import SyncStatusTracker
from integrations.hrms.sync.tasks import sync_organization_data
from .utils import is_org_admin

@login_required
@user_passes_test(is_org_admin)
def hrms_integration(request):
    """View to manage HRMS System route configurations and manual sync triggers."""
    org = request.user.organization
    
    # Get or create an inactive config placeholder
    config, created = HRMSSystemConfig.objects.get_or_create(organization=org)
    
    tracker = SyncStatusTracker()
    
    if request.method == "POST":
        action = request.POST.get("action")
        
        if action == "unlock_hrms_config":
            edit_token = request.POST.get("edit_token")
            
            # Validate Edit Token
            if not config.edit_token or edit_token != config.edit_token:
                messages.error(request, "Invalid Authorization Token. Configuration unlocking failed.")
                return redirect('hrms_integration')
                
            if config.edit_token_expires_at and timezone.now() > config.edit_token_expires_at:
                messages.error(request, "Edit Token expired. Please generate a new one from the Admin portal.")
                return redirect('hrms_integration')
                
            request.session['hrms_config_unlocked'] = True
            messages.success(request, "Configuration unlocked for editing.")
            return redirect('hrms_integration')

        elif action == "update_hrms_config":
            if not request.session.get('hrms_config_unlocked'):
                messages.error(request, "Session expired or configuration not unlocked.")
                return redirect('hrms_integration')
            
            # Save new valid configuration
            config.hrms_type = request.POST.get("hrms_type")
            config.base_url = request.POST.get("base_url")
            
            new_auth = request.POST.get("auth_token")
            if new_auth and new_auth != "********":
                config.auth_token = new_auth
                
            config.departments_endpoint = request.POST.get("departments_endpoint")
            config.employees_endpoint = request.POST.get("employees_endpoint")
            config.jobs_endpoint = request.POST.get("jobs_endpoint")
            config.candidates_endpoint = request.POST.get("candidates_endpoint")
            config.interviews_endpoint = request.POST.get("interviews_endpoint")
            config.onboarding_endpoint = request.POST.get("onboarding_endpoint")
            config.is_active = True
            
            # Expire token immediately after successful usage so it's a one-time-use per UI save
            config.edit_token = None
            config.edit_token_expires_at = None
            
            config.save()
            request.session.pop('hrms_config_unlocked', None)
            messages.success(request, "HRMS mapping successfully updated and locked.")
            return redirect('hrms_integration')
            
        elif action == "force_stop_sync":
            running_sync_id = tracker.get_latest_running_sync_id(org.id, 'batch_all')
            if running_sync_id:
                tracker.request_stop(org.id)
                messages.warning(request, "Force-stop signal sent. The sync will halt at its next checkpoint.")
            else:
                messages.info(request, "No sync is currently running.")
            return redirect('hrms_integration')

        elif action == "trigger_hrms_sync":
            print(f"[DEBUG] trigger_hrms_sync called for organization: {org.id}")
            print(f"[DEBUG] config.is_active: {config.is_active}")
            
            if not config.is_active:
                print("[DEBUG] Aborting: config is inactive.")
                messages.error(request, "Cannot sync inactive HRMS configuration.")
                return redirect('hrms_integration')
                
            last_sync_time = tracker.get_last_sync_time(org.id, 'batch_all')
            latest_status = tracker.get_latest_sync_status(org.id, 'batch_all')
            print(f"[DEBUG] last_sync_time: {last_sync_time}")
            print(f"[DEBUG] latest_status: {latest_status}")
            
            is_running = latest_status and latest_status.get('status') == 'running'
            print(f"[DEBUG] is_running: {is_running}")
            
            if is_running:
                print("[DEBUG] Aborting: A synchronization job is already running.")
                messages.warning(request, "A synchronization job is already running.")
            elif last_sync_time and (timezone.now() - last_sync_time).total_seconds() < 900: # 15 minutes limit
                time_diff = (timezone.now() - last_sync_time).total_seconds()
                print(f"[DEBUG] Aborting: 15 minutes limit (Wait time: {time_diff}s)")
                messages.warning(request, "Please wait 15 minutes between manual syncs.")
            else:
                try:
                    print(f"[DEBUG] Calling sync_organization_data.delay({org.id})")
                    result = sync_organization_data.delay(org.id)
                    print(f"[DEBUG] Celery task queued with ID: {result.id}")
                    messages.success(request, "Background HRMS Synchronization successfully queued!")
                except Exception as e:
                    print(f"[DEBUG] Failed to queue sync task: {e}")
                    messages.error(request, f"Failed to queue sync task: {e}")
                    
            return redirect('hrms_integration')

    # Status check calculating the sync cooldown badge
    last_sync_time = tracker.get_last_sync_time(org.id, 'batch_all')
    latest_status = tracker.get_latest_sync_status(org.id, 'batch_all')
    is_sync_running = latest_status and latest_status.get('status') == 'running'
    minutes_remaining = 0
    is_sync_disabled = False
    
    if is_sync_running:
        is_sync_disabled = True
    elif last_sync_time:
        seconds_passed = (timezone.now() - last_sync_time).total_seconds()
        if seconds_passed < 900:
            is_sync_disabled = True
            minutes_remaining = int((900 - seconds_passed) / 60)

    is_unlocked = request.session.get('hrms_config_unlocked', False)

    return render(request, 'hrms_integration.html', {
        'config': config,
        'is_active': config.is_active and bool(config.base_url),
        'is_sync_running': is_sync_running,
        'is_sync_disabled': is_sync_disabled,
        'minutes_remaining': minutes_remaining,
        'is_unlocked': is_unlocked
    })
