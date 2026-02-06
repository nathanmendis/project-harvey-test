from core.models import LeaveRequest
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from .utils import is_org_admin

@login_required
@user_passes_test(is_org_admin)
def leaves(request):
    """View to display list of pending leave requests."""
    org = request.user.organization
    leaves = LeaveRequest.objects.filter(organization=org, status='pending')
    
    return render(request, 'recruitment/leaves.html', {
        'org': org,
        'leaves': leaves,
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
