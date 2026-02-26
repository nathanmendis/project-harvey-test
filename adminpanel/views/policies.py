from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from core.models.policy import Policy
from core.ai.rag.policy_indexer import PolicyIndexer
from django.db.models import Q
from django.core.paginator import Paginator
import threading
from .utils import is_org_admin

@login_required
@user_passes_test(is_org_admin)
def manage_policies(request):
    """View and manage organization policies."""
    org = request.user.organization
    query = request.GET.get('q', '').strip()
    
    policies_list = Policy.objects.filter(created_by__organization=org).order_by('-created_at')
    
    if query:
        policies_list = policies_list.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query)
        )
        
    paginator = Paginator(policies_list, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, "policies/manage.html", {
        "policies": page_obj,
        "page_obj": page_obj,
        "paginator": paginator,
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
                return render(request, "policies/add.html", {"org": org})
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

    return render(request, "policies/add.html", {"org": org})


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
