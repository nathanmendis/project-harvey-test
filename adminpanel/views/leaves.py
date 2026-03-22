from core.models import LeaveRequest
from core.models.leaves import LeaveBalance
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from .utils import is_org_admin ,is_admin_manager_hr

@login_required
@user_passes_test(is_admin_manager_hr)
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
    
    return render(request, 'leaves/leaves.html', {
        'org': org,
        'leaves': page_obj,
        'page_obj': page_obj,
        'paginator': paginator,
    })

@login_required
@user_passes_test(is_admin_manager_hr)
def leave_detail(request, leave_id):
    """View to display leave details."""
    org = request.user.organization
    leave = get_object_or_404(LeaveRequest, id=leave_id, organization=org)
    
    year = leave.start_date.year
    balance = LeaveBalance.objects.filter(employee=leave.employee, organization=org, year=year, leave_type=leave.leave_type).first()
    
    return render(request, 'leaves/leave_detail.html', {
        'org': org,
        'leave': leave,
        'balance': balance,
    })

@login_required
@user_passes_test(is_admin_manager_hr)
def approve_leave(request, leave_id):
    """View to approve a leave request."""
    org = request.user.organization
    leave = get_object_or_404(LeaveRequest, id=leave_id, organization=org)
    
    if request.method == "POST":
        leave.status = 'approved'
        leave.save()
        
        # Dispatch Email
        try:
            from integrations.google.gmail import GmailService
            gmail_service = GmailService()
            subject = f"Leave Request Approved! - {leave.start_date}"
            body = f"Hi {leave.employee.name or leave.employee.username},\n\nGood news! Your leave request for {leave.leave_type} from {leave.start_date} to {leave.end_date} has been approved.\n\nEnjoy your time off!\n\nThanks,\n{org.name} HR"
            gmail_service.send_email(recipient_email=leave.employee.email, subject=subject, body=body)
        except Exception as e:
            print(f"Failed to send approval email: {e}")

        messages.success(request, f"Leave request for {leave.employee.username} has been approved.")
        return redirect('leave_detail', leave_id=leave.id)
    
    return redirect('leave_detail', leave_id=leave.id)

@login_required
@user_passes_test(is_admin_manager_hr)
def reject_leave(request, leave_id):
    """View to reject a leave request."""
    org = request.user.organization
    leave = get_object_or_404(LeaveRequest, id=leave_id, organization=org)
    
    if request.method == "POST":
        # Dispatch Email
        try:
            from integrations.google.gmail import GmailService
            gmail_service = GmailService()
            subject = f"Leave Request Rejected - {leave.start_date}"
            body = f"Hi {leave.employee.name or leave.employee.username},\n\nYour leave request for {leave.leave_type} from {leave.start_date} to {leave.end_date} has unfortunately been rejected by your manager.\n\nPlease reach out if you have any questions.\n\nThanks,\n{org.name} HR"
            gmail_service.send_email(recipient_email=leave.employee.email, subject=subject, body=body)
        except Exception as e:
            print(f"Failed to send rejection email: {e}")
            
        employee_name = leave.employee.username
        # Delete the rejected request from the database as requested
        leave.delete()
        
        messages.success(request, f"Leave request for {employee_name} has been rejected and permanently removed from the records.")
        # Redirect back to the list view, since the detail page no longer exists
        return redirect('leaves')
    
    return redirect('leaves')
