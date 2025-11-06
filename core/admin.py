from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.contrib.auth.hashers import make_password
from .models import Organization, User


# ─────────────────────────────
# Inline: Show Org Users under Organization
# ─────────────────────────────
class UserInline(admin.TabularInline):
    model = User
    fields = ("username", "email", "role", "is_active", "has_chat_access")
    extra = 0
    readonly_fields = ("username", "email", "role", "is_active")
    can_delete = False


# ─────────────────────────────
# Organization Admin
# ─────────────────────────────
@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "org_id", "domain", "created_at", "updated_at", "add_org_admin_button")
    search_fields = ("name", "org_id", "domain")
    inlines = [UserInline]

    def add_org_admin_button(self, obj):
        """Button to create Org Admins directly from org page."""
        return format_html(
            f'<a href="/admin/core/user/add/?organization={obj.id}&role=org_admin" '
            f'style="background-color:#4f46e5;color:white;padding:4px 10px;border-radius:5px;text-decoration:none;">'
            f'➕ Add Org Admin</a>'
        )
    add_org_admin_button.short_description = "Actions"


# ─────────────────────────────
# Custom User Admin
# ─────────────────────────────
@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("username", "email", "organization", "role", "has_chat_access", "is_active")
    list_filter = ("role", "organization", "is_active")
    search_fields = ("username", "email", "organization__name")
    ordering = ("organization", "username")

    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Personal Info", {"fields": ("name", "email", "organization", "role", "has_chat_access")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Important Dates", {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": (
                "username",
                "email",
                "name",
                "password1",
                "password2",
                "organization",
                "role",
                "has_chat_access",
            ),
        }),
    )

    def get_changeform_initial_data(self, request):
        """Auto-fill organization & role when adding user from org page."""
        initial = super().get_changeform_initial_data(request)
        org_id = request.GET.get("organization")
        role = request.GET.get("role")
        if org_id:
            initial["organization"] = org_id
        if role:
            initial["role"] = role
        return initial

    def save_model(self, request, obj, form, change):
        """Auto-hash password if creating manually through admin."""
        if not change and not obj.password:
            obj.password = make_password(obj.password)
        super().save_model(request, obj, form, change)


# ─────────────────────────────
# Customize Admin Branding
# ─────────────────────────────
admin.site.site_header = "Harvey Admin Panel"
admin.site.index_title = "Harvey Administration"
admin.site.site_title = "Harvey Admin"
