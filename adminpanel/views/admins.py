from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from core.models.organization import User
from .utils import is_org_admin

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

    return render(request, "admins/add.html", {"org": org})


@login_required
@user_passes_test(is_org_admin)
def manage_org_admins(request):
    """View and manage all organization admins within your organization."""
    org = request.user.organization
    admins = User.objects.filter(organization=org, role="org_admin")

    return render(request, "admins/manage.html", {
        "admins": admins,
        "org": org
    })
