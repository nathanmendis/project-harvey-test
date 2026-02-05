from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.core.mail import send_mail
from django.utils import timezone
from datetime import timedelta
from core.models.invite import Invite
from adminpanel.forms import InviteForm
from .utils import is_org_admin

@login_required
@user_passes_test(is_org_admin)
def invite_user(request):
    """Invite a new user via email."""
    org = request.user.organization

    if request.method == "POST":
        form = InviteForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            role = form.cleaned_data['role']
            
            # Check for pending valid invites
            existing_invite = Invite.objects.filter(email=email, accepted=False, expires_at__gt=timezone.now()).first()
            if existing_invite:
                messages.warning(request, f"A pending invite already exists for {email}.")
                return redirect('admin_dashboard')

            # Check if user already exists
            if User.objects.filter(email=email).exists():
                messages.error(request, f"User with email {email} already exists.")
                return redirect('admin_dashboard')

            invite = form.save(commit=False)
            invite.organization = org
            invite.created_by = request.user
            invite.expires_at = timezone.now() + timedelta(days=7)
            invite.save()

            # "Send" email (Console Backend)
            invite_link = request.build_absolute_uri(f"/auth/google/login?invite={invite.token}")
            print(f"\n[EMAIL MOCK] To: {email}\nSubject: You're invited to join {org.name}\nBody: Click here to join: {invite_link}\n")
            
            # Actual send_mail call (will go to console if configured, or just be logged above)
            try:
                send_mail(
                    subject=f"Invitation to join {org.name}",
                    message=f"You have been invited to join {org.name} as a {invite.get_role_display()}.\n\nClick here to join: {invite_link}",
                    from_email=None, # Default
                    recipient_list=[email],
                    fail_silently=True
                )
            except Exception as e:
                print(f"Error sending email: {e}")
                messages.error(request, f"Error sending email: {e}")

            messages.success(request, f"Invite sent to {email}.")
            return redirect('manage_employees')
    else:
        form = InviteForm()
    
    return render(request, 'employees/add.html', {'form': form, 'org': org})

@login_required
def manage_invites(request):
    """View to list pending invites."""
    if not request.user.is_org_admin():
        messages.error(request, "Access denied.")
        return redirect('admin_dashboard')
        
    org = request.user.organization
    invites = Invite.objects.filter(organization=org, accepted=False).order_by('-created_at')
    
    return render(request, 'invites/manage.html', {'invites': invites})

@login_required
def delete_invite(request, invite_id):
    """View to revoke/delete a pending invite."""
    if not request.user.is_org_admin():
        messages.error(request, "Access denied.")
        return redirect('admin_dashboard')
        
    org = request.user.organization
    invite = get_object_or_404(Invite, id=invite_id, organization=org)
    
    email = invite.email
    invite.delete()
    messages.success(request, f"Invite for {email} has been revoked.")
    
    return redirect('manage_invites')
