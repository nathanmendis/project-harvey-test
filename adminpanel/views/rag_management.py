import logging
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.views.decorators.http import require_POST

from core.models.policy import Policy
from core.models.recruitment import Candidate, JobRole
from .utils import is_org_admin, is_admin_manager_hr

logger = logging.getLogger("harvey")


@login_required
@user_passes_test(is_org_admin)
def rag_dashboard(request):
    """Render the RAG pipeline management dashboard."""
    if not request.user.is_org_admin():
        messages.error(request, "Access Denied: RAG Management is restricted to Organization Admins only.")
        return redirect('admin_dashboard')

    org = request.user.organization

    policy_count = Policy.objects.filter(created_by__organization=org).count()
    indexed_policy_count = Policy.objects.filter(
        created_by__organization=org, status="indexed"
    ).count()

    candidate_count = Candidate.objects.filter(organization=org).count()
    job_count = JobRole.objects.filter(organization=org).count()

    return render(
        request,
        "rag_management/index.html",
        {
            "org": org,
            "policy_count": policy_count,
            "indexed_policy_count": indexed_policy_count,
            "candidate_count": candidate_count,
            "job_count": job_count,
        },
    )


@login_required
@user_passes_test(is_org_admin)
@require_POST
def reindex_all_policies(request):
    """Trigger background re-indexing of all org policies."""
    if not request.user.is_org_admin():
        messages.error(request, "Access Denied: RAG Management is restricted to Organization Admins only.")
        return redirect('admin_dashboard')

    from core.tasks import reindex_all_policies_task

    org = request.user.organization
    reindex_all_policies_task.delay(organization_id=str(org.id))
    messages.success(
        request,
        f"Policy reindexing queued for \"{org.name}\". This runs in the background.",
    )
    return redirect("rag_dashboard")


@login_required
@user_passes_test(is_org_admin)
@require_POST
def reindex_all_candidates(request):
    """Trigger background re-indexing of all org candidates."""
    if not request.user.is_org_admin():
        messages.error(request, "Access Denied: RAG Management is restricted to Organization Admins only.")
        return redirect('admin_dashboard')

    from core.tasks import reindex_all_candidates_task

    org = request.user.organization
    reindex_all_candidates_task.delay(organization_id=str(org.id))
    messages.success(
        request,
        f"Candidate reindexing queued for \"{org.name}\". This runs in the background.",
    )
    return redirect("rag_dashboard")


@login_required
@user_passes_test(is_org_admin)
@require_POST
def reindex_all_jobs(request):
    """Trigger background re-indexing of all org job roles."""
    if not request.user.is_org_admin():
        messages.error(request, "Access Denied: RAG Management is restricted to Organization Admins only.")
        return redirect('admin_dashboard')

    from core.tasks import reindex_all_jobs_task

    org = request.user.organization
    reindex_all_jobs_task.delay(organization_id=str(org.id))
    messages.success(
        request,
        f"Job reindexing queued for \"{org.name}\". This runs in the background.",
    )
    return redirect("rag_dashboard")


@login_required
@user_passes_test(is_org_admin)
@require_POST
def reindex_everything(request):
    """Trigger background re-indexing of ALL data types for the org."""
    if not request.user.is_org_admin():
        messages.error(request, "Access Denied: RAG Management is restricted to Organization Admins only.")
        return redirect('admin_dashboard')

    from core.tasks import (
        reindex_all_policies_task,
        reindex_all_candidates_task,
        reindex_all_jobs_task,
    )

    org = request.user.organization
    org_id = str(org.id)
    reindex_all_policies_task.delay(organization_id=org_id)
    reindex_all_candidates_task.delay(organization_id=org_id)
    reindex_all_jobs_task.delay(organization_id=org_id)
    messages.success(
        request,
        f"⚡ Full reindex queued for \"{org.name}\" — policies, candidates & jobs are all being re-indexed in the background.",
    )
    return redirect("rag_dashboard")
