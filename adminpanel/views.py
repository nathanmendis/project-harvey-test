from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from core.models.organization import User, Organization
from core.models.policy import Policy
from core.services.policy_indexer import PolicyIndexer
import threading

from django.http import JsonResponse
from django.db.models import Q
from django.core.mail import send_mail
from django.utils import timezone
from datetime import timedelta
from .forms import InviteForm
from core.models.invite import Invite


def is_org_admin(user):
    return user.is_authenticated and (user.role == "org_admin" or user.is_superuser)


# Admin Dashboard

@login_required
@user_passes_test(is_org_admin)
def admin_dashboard(request):
    """Admin dashboard with user and chatbot management."""
    org = request.user.organization
    
    total_users = User.objects.filter(organization=org).count()
    admin_users = User.objects.filter(organization=org, role="org_admin").count()
    staff_users = User.objects.filter(organization=org, is_staff=True).count()
    regular_users = User.objects.filter(organization=org, is_staff=False).count()

    def get_pct(count):
        return (count / total_users * 100) if total_users > 0 else 0

    context = {
        "org_name": org.name if org else "No Organization",
        "total_users": total_users,
        "admin_users": admin_users,
        "staff_users": staff_users,
        "regular_users": regular_users,
        "admin_pct": get_pct(admin_users),
        "staff_pct": get_pct(staff_users),
        "regular_pct": get_pct(regular_users),
    }
    return render(request, "dashboard.html", context)



# Add Employee

@login_required
@user_passes_test(is_org_admin)
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
                    from integrations.services.google.gmail import GmailService
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

    return render(request, "add_employee.html", {"org": org, "invite_form": invite_form})


# Manage Employees

@login_required
@user_passes_test(is_org_admin)
def manage_employees(request):
    """View all employees in the organization."""
    org = request.user.organization
    employees = User.objects.filter(organization=org, is_superuser=False)

    return render(request, "manage_employees.html", {
        "employees": employees,
        "org": org
    })



# Remove Employee

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

# Toggle Chatbot Access

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
        messages.info(request, f"👤 {user.username} is no longer an Org Admin.")
    else:
        user.role = "org_admin"
        messages.success(request, f"⭐ {user.username} is now an Org Admin.")

    user.save()
    return redirect("manage_employees")

@login_required
@user_passes_test(is_org_admin)
def add_org_admin(request):
    """Allow an organization admin to add another admin within the same org."""
    org = request.user.organization

    if request.method == "POST":
        name = request.POST.get("name")
        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password")

        # Validation
        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists.")
            return redirect("add_org_admin")
        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already in use.")
            return redirect("add_org_admin")

        # Create new admin
        new_admin = User.objects.create(
            username=username,
            email=email,
            password=password,
            name=name,
            role="org_admin",
            organization=org,
            is_staff=True,  # Optional: lets them access org tools
        )

        messages.success(request, f"Org Admin '{username}' added successfully!")
        return redirect("manage_org_admins")

    return render(request, "add_org_admin.html", {"org": org})


@login_required
@user_passes_test(is_org_admin)
def manage_org_admins(request):
    """View and manage all organization admins within your organization."""
    org = request.user.organization
    admins = User.objects.filter(organization=org, role="org_admin")

    return render(request, "manage_org_admins.html", {
        "admins": admins,
        "org": org
    })


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


# ─────────────────────────────
# Policy Management
# ─────────────────────────────

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
    
    return render(request, 'add_employee.html', {'form': form, 'org': org})

@login_required
def manage_invites(request):
    """View to list pending invites."""
    if not request.user.is_org_admin():
        messages.error(request, "Access denied.")
        return redirect('admin_dashboard')
        
    org = request.user.organization
    invites = Invite.objects.filter(organization=org, accepted=False).order_by('-created_at')
    
    return render(request, 'manage_invites.html', {'invites': invites})

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