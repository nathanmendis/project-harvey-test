from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from core.models.policy import Policy
from core.services.policy_indexer import PolicyIndexer
import threading
from .utils import is_org_admin

@login_required
@user_passes_test(is_org_admin)
def manage_policies(request):
    """View and manage organization policies."""
    org = request.user.organization
    policies = Policy.objects.filter(created_by__organization=org).order_by('-created_at')

    return render(request, "manage_policies.html", {
        "policies": policies,
        "org": org
    })


@login_required
@user_passes_test(is_org_admin)
def add_policy(request):
    """Add a new policy."""
    org = request.user.organization

    if request.method == "POST":
        title = request.POST.get("title")
        description = request.POST.get("description")
        source_type = request.POST.get("source_type")
        
        policy = Policy(
            title=title,
            description=description,
            source_type=source_type,
            created_by=request.user
        )

        if source_type == "upload":
            if "uploaded_file" in request.FILES:
                policy.uploaded_file = request.FILES["uploaded_file"]
            else:
                messages.error(request, "Please select a file to upload.")
                return render(request, "add_policy.html", {"org": org})
        elif source_type == "url":
            policy.external_url = request.POST.get("external_url")
        
        try:
            policy.save()
            
            # Auto-trigger indexing
            indexer = PolicyIndexer()
            thread = threading.Thread(target=indexer.index_policy, args=(policy.id,))
            thread.start()
            
            messages.success(request, f"Policy '{title}' added and indexing started.")
            return redirect("manage_policies")
        except Exception as e:
            messages.error(request, f"Error adding policy: {e}")

    return render(request, "add_policy.html", {"org": org})


@login_required
@user_passes_test(is_org_admin)
def reindex_policy(request, policy_id):
    """Trigger re-indexing for a policy."""
    org = request.user.organization
    policy = get_object_or_404(Policy, id=policy_id, created_by__organization=org)

    indexer = PolicyIndexer()
    thread = threading.Thread(target=indexer.index_policy, args=(policy.id,))
    thread.start()

    messages.success(request, f"Re-indexing started for '{policy.title}'.")
    return redirect("manage_policies")


@login_required
@user_passes_test(is_org_admin)
def delete_policy(request, policy_id):
    """Delete a policy."""
    org = request.user.organization
    policy = get_object_or_404(Policy, id=policy_id, created_by__organization=org)

    policy.delete()
    messages.success(request, f"Policy '{policy.title}' deleted successfully.")
    return redirect("manage_policies")
