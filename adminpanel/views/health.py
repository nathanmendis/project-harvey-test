import os
import time
import redis
import logging
from django.conf import settings
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from adminpanel.views.utils import is_org_admin
from project_harvey.celery import app as celery_app

logger = logging.getLogger("harvey")

@login_required
@user_passes_test(is_org_admin)
def system_health_page(request):
    """Renders the system health dashboard UI container."""
    org = request.user.organization
    return render(request, "settings/health.html", {
        "org": org,
    })

@login_required
@user_passes_test(is_org_admin)
def system_health_api(request):
    """
    API endpoint running real-time diagnostics on Redis, Celery, and Environment configurations.
    Returns status in JSON format.
    """
    org = request.user.organization
    
    # 1. Redis Diagnosis
    redis_status = "unhealthy"
    redis_latency = None
    redis_error = None
    try:
        t0 = time.time()
        # Extract Redis location from settings
        redis_loc = settings.CACHES.get('default', {}).get('LOCATION', 'redis://localhost:6379/1')
        r = redis.from_url(redis_loc)
        r.ping()
        t1 = time.time()
        redis_status = "healthy"
        redis_latency = round((t1 - t0) * 1000, 2)
    except Exception as e:
        redis_error = str(e)
        logger.error(f"Health check Redis error: {e}")

    # 2. Celery Diagnosis
    celery_status = "unhealthy"
    active_workers = []
    try:
        # inspect() fetches worker info from Redis/broker
        inspect = celery_app.control.inspect(timeout=1.5)
        ping_res = inspect.ping()
        if ping_res:
            celery_status = "healthy"
            active_workers = list(ping_res.keys())
    except Exception as e:
        logger.error(f"Health check Celery error: {e}")

    # 3. System Environment Variables
    env_keys = [
        "GROQ_API_KEY",
        "GEMINI_API_KEY",
        "GOOGLE_API_KEY",
        "GOOGLE_CLIENT_ID",
        "GOOGLE_CLIENT_SECRET",
        "GOOGLE_SYSTEM_REFRESH_TOKEN",
        "FIELD_ENCRYPTION_KEY",
    ]
    
    system_env = {}
    for key in env_keys:
        val = os.environ.get(key) or getattr(settings, key, None)
        is_configured = bool(val)
        system_env[key] = {
            "status": "configured" if is_configured else "missing",
            "value": f"{val[:6]}..." if (is_configured and len(str(val)) > 8) else "N/A"
        }

    # 4. Org-Specific Integrations
    # Check Google Workspace Integration
    google_configured = bool(org.google_refresh_token)
    
    # Check HRMS Integration
    hrms_configured = False
    hrms_type = "N/A"
    try:
        if hasattr(org, 'hrms_system_config') and org.hrms_system_config:
            hrms_configured = org.hrms_system_config.is_active
            hrms_type = org.hrms_system_config.hrms_type
    except Exception:
        pass

    org_integrations = {
        "google_workspace": {
            "status": "connected" if google_configured else "disconnected",
            "email": org.google_connected_email or "Not connected"
        },
        "hrms": {
            "status": "active" if hrms_configured else "inactive",
            "type": hrms_type
        }
    }

    # Overall calculation
    overall_status = "healthy"
    if redis_status == "unhealthy" or celery_status == "unhealthy":
        overall_status = "unhealthy"

    return JsonResponse({
        "status": overall_status,
        "timestamp": time.time(),
        "redis": {
            "status": redis_status,
            "latency_ms": redis_latency,
            "error": redis_error,
        },
        "celery": {
            "status": celery_status,
            "active_workers": active_workers,
        },
        "system_env": system_env,
        "org_integrations": org_integrations,
    })
