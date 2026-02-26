from core.models import LeaveRequest
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from .utils import is_org_admin

@login_required
@user_passes_test(is_org_admin)
def leaves(request):
    """View to display list of pending leave requests."""
    org = request.user.organization
    query = request.GET.get('q', '').strip()
    
    leaves_list = LeaveRequest.objects.filter(organization=org).order_by('-id')
    
    if query:
        leaves_list = leaves_list.filter(
            Q(employee__name__icontains=query) |
            Q(status__icontains=query) |
            Q(leave_type__icontains=query)
        )
        
    paginator = Paginator(leaves_list, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'recruitment/leaves.html', {
        'org': org,
        'leaves': page_obj,
        'page_obj': page_obj,
        'paginator': paginator,
    })

@login_required
@user_passes_test(is_org_admin)
def leave_detail(request, leave_id):
    """View to display leave details."""
    org = request.user.organization
    leave = get_object_or_404(LeaveRequest, id=leave_id, organization=org)
    
    return render(request, 'recruitment/leave_detail.html', {
        'org': org,
        'leave': leave,
    })

@login_required
@user_passes_test(is_org_admin)
def approve_leave(request, leave_id):
    """View to approve a leave request."""
    org = request.user.organization
    leave = get_object_or_404(LeaveRequest, id=leave_id, organization=org)
    
    if request.method == "POST":
        leave.status = 'approved'
        leave.save()
        messages.success(request, f"Leave request for {leave.employee.username} has been approved.")
        return redirect('leave_detail', leave_id=leave.id)
    
    return redirect('leave_detail', leave_id=leave.id)
