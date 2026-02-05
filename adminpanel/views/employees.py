from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta
from core.models.organization import User
from core.models.invite import Invite
from adminpanel.forms import InviteForm
from .utils import is_org_admin

@login_required
@user_passes_test(is_org_admin)
def add_employee(request):
    """Add new employee (Invite or Manual)."""
    org = request.user.organization
    invite_form = InviteForm()

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "invite":
            invite_form = InviteForm(request.POST)
            if invite_form.is_valid():
                email = invite_form.cleaned_data['email']
                role = invite_form.cleaned_data['role']
                
                # Check for pending valid invites
                existing_invite = Invite.objects.filter(email=email, accepted=False, expires_at__gt=timezone.now()).first()
                if existing_invite:
                    messages.warning(request, f"A pending invite already exists for {email}.")
                    return redirect("add_employee")

                # Check if user already exists
                if User.objects.filter(email=email).exists():
                    messages.error(request, f"User with email {email} already exists.")
                    return redirect("add_employee")

                invite = invite_form.save(commit=False)
                invite.organization = org
                invite.created_by = request.user
                invite.expires_at = timezone.now() + timedelta(days=7)
                invite.save()

                # "Send" email via Gmail API
                invite_link = request.build_absolute_uri(f"/auth/google/login?invite={invite.token}")
                
                # Render HTML email
                from django.template.loader import render_to_string
                from django.utils.html import strip_tags

                html_content = render_to_string('emails/invite_email.html', {
                    'org_name': org.name,
                    'org_id': org.id,
                    'role': invite.get_role_display(),
                    'inviter_name': request.user.get_full_name() or request.user.username,
                    'inviter_email': request.user.email,
                    'invite_link': invite_link,
                })
                text_content = strip_tags(html_content)

                try:
                    from integrations.google.gmail import GmailService
                    # No user needed, uses system token
                    gmail_service = GmailService() 
                    
                    gmail_service.send_email(
                        recipient_email=email,
                        subject=f"Invitation to join {org.name} on Project Harvey",
                        body=text_content,
                        html_content=html_content
                    )
                    messages.success(request, f"Invite sent to {email} from Team Harvey.")
                
                except ValueError as e:
                    # Token missing
                    messages.warning(request, f"Invite created, but email failed: {e}. Check GOOGLE_SYSTEM_REFRESH_TOKEN in .env.")
                except Exception as e:
                    print(f"Error sending email: {e}")
                    messages.error(request, f"Error sending email: {e}")
                
                return redirect("manage_employees")

        elif action == "create":
            name = request.POST.get("name")
            username = request.POST.get("username")
            email = request.POST.get("email")
            password = request.POST.get("password")
            role = request.POST.get("role", "employee")
            chatbot_access = bool(request.POST.get("chatbot_access"))

            if User.objects.filter(username=username).exists():
                messages.error(request, "Username already exists.")
                return redirect("add_employee")

            new_user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                name=name,
                role=role,
                organization=org,
            )
            new_user.has_chat_access = chatbot_access
            new_user.save()

            messages.success(request, f"Employee '{username}' created manually.")
            return redirect("manage_employees")

    return render(request, "employees/add.html", {"org": org, "invite_form": invite_form})


@login_required
@user_passes_test(is_org_admin)
def manage_employees(request):
    """View all employees in the organization."""
    org = request.user.organization
    employees = User.objects.filter(organization=org, is_superuser=False)

    return render(request, "employees/manage.html", {
        "employees": employees,
        "org": org
    })


@login_required
@user_passes_test(is_org_admin)
def remove_employee(request, user_id):
    """Remove an employee from the organization."""
    org = request.user.organization
    user = get_object_or_404(User, id=user_id, organization=org)

    if user.is_superuser or user.is_staff:
        messages.error(request, "You cannot delete another admin.")
    else:
        user.delete()
        messages.success(request, f"Employee '{user.username}' removed successfully.")

    return redirect("manage_employees")


@login_required
@user_passes_test(is_org_admin)
def toggle_chat_access(request, user_id):
    """Enable or disable chatbot access for an employee."""
    org = request.user.organization
    user = get_object_or_404(User, id=user_id, organization=org)

    user.has_chat_access = not getattr(user, "has_chat_access", True)
    user.save()

    status = "enabled" if user.has_chat_access else "disabled"
    messages.success(request, f"Chatbot access {status} for {user.username}.")
    return redirect("manage_employees")


@login_required
@user_passes_test(is_org_admin)
def toggle_admin_role(request, user_id):
    """Promote or demote an employee to/from Org Admin."""
    org = request.user.organization
    user = get_object_or_404(User, id=user_id, organization=org)

    if user == request.user:
        messages.error(request, "You cannot change your own role.")
        return redirect("manage_employees")

    # Toggle between 'org_admin' and 'employee'
    if user.role == "org_admin":
        user.role = "employee"
        messages.info(request, f" {user.username} is no longer an Org Admin.")
    else:
        user.role = "org_admin"
        messages.success(request, f" {user.username} is now an Org Admin.")

    user.save()
    return redirect("manage_employees")


@login_required
@user_passes_test(is_org_admin)
def search_employee(request):
    """Search employees by username, email, or ID."""
    query = request.GET.get("q", "").strip()
    org = request.user.organization

    if not query:
        return JsonResponse({"results": []})

    employees = User.objects.filter(
        organization=org
    ).filter(
        Q(username__icontains=query) |
        Q(email__icontains=query) |
        Q(id__icontains=query) |
        Q(name__icontains=query)
    ).values("id", "name", "username", "email", "role", "has_chat_access")

    return JsonResponse({"results": list(employees)})
