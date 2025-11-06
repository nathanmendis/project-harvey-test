from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from core.models import User


def is_admin(user):
    return user.is_staff or user.is_superuser



# Admin Dashboard

@login_required
@user_passes_test(is_admin)
def admin_dashboard(request):
    """Admin dashboard with user and chatbot management."""
    org = request.user.organization

    context = {
        "org_name": org.name if org else "No Organization",
        "total_users": User.objects.filter(organization=org).count(),
        "staff_users": User.objects.filter(organization=org, is_staff=True).count(),
        "regular_users": User.objects.filter(organization=org, is_staff=False).count(),
    }
    return render(request, "dashboard.html", context)



# Add Employee

@login_required
@user_passes_test(is_admin)
def add_employee(request):
    """Add new employee to admin’s organization."""
    org = request.user.organization

    if request.method == "POST":
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
        new_user.has_chat_access = chatbot_access  # optional custom field
        new_user.save()

        messages.success(request, f"Employee '{username}' added successfully.")
        return redirect("manage_employees")

    return render(request, "add_employee.html", {"org": org})


# Manage Employees

@login_required
@user_passes_test(is_admin)
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
@user_passes_test(is_admin)
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
@user_passes_test(is_admin)
def toggle_chat_access(request, user_id):
    """Enable or disable chatbot access for an employee."""
    org = request.user.organization
    user = get_object_or_404(User, id=user_id, organization=org)

    user.has_chat_access = not getattr(user, "has_chat_access", True)
    user.save()

    status = "enabled" if user.has_chat_access else "disabled"
    messages.success(request, f"Chatbot access {status} for {user.username}.")
    return redirect("manage_employees")


