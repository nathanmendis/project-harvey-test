from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.contrib.auth.hashers import make_password
from .models import Organization, User, Policy, PolicyChunk, AppLog
from .models.recruitment import (
    Candidate, JobRole, Interview, EmailLog, 
    CalendarEvent, CandidateJobScore, HRMSSystemConfig
)
from .models.leaves import (
    OrganizationLeavePolicy, LeaveBalance, LeaveSystemConfig, LeaveRequest
)
from core.ai.rag.policy_indexer import PolicyIndexer
import threading


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

    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path('<int:org_id>/generate-hrms-token/', self.admin_site.admin_view(self.generate_hrms_token_view), name='core_organization_generate_hrms_token'),
            path('<int:org_id>/generate-leave-token/', self.admin_site.admin_view(self.generate_leave_token_view), name='core_organization_generate_leave_token'),
        ]
        return custom_urls + urls

    def generate_hrms_token_view(self, request, org_id):
        from django.shortcuts import get_object_or_404, redirect
        from .models.recruitment import HRMSSystemConfig
        org = get_object_or_404(Organization, pk=org_id)
        config, created = HRMSSystemConfig.objects.get_or_create(organization=org)
        token = config.generate_edit_token()
        self.message_user(request, f"Generated new HRMS Edit Token for {org.name}. Token: {token} (Valid for 24h)")
        return redirect('admin:core_organization_changelist')

    def generate_leave_token_view(self, request, org_id):
        from django.shortcuts import get_object_or_404, redirect
        from .models.leaves import LeaveSystemConfig
        org = get_object_or_404(Organization, pk=org_id)
        config, created = LeaveSystemConfig.objects.get_or_create(organization=org)
        token = config.generate_edit_token()
        self.message_user(request, f"Generated new Leave Policies Edit Token for {org.name}. Token: {token} (Valid for 24h)")
        return redirect('admin:core_organization_changelist')

    def add_org_admin_button(self, obj):
        """Action buttons directly on the org page."""
        from django.urls import reverse
        try:
            token_url = reverse('admin:core_organization_generate_hrms_token', args=[obj.id])
        except Exception:
            token_url = "#"
            
        try:
            leave_token_url = reverse('admin:core_organization_generate_leave_token', args=[obj.id])
        except Exception:
            leave_token_url = "#"
            
        return format_html(
            '<div style="display:flex; gap:8px;">'
            '<a href="/admin/core/user/add/?organization={}&role=org_admin" '
            'style="background-color:#4f46e5;color:white;padding:4px 10px;border-radius:5px;text-decoration:none;font-weight:bold;">'
            ' Add Org Admin</a>'
            '<a href="{}" '
            'style="background-color:#10b981;color:white;padding:4px 10px;border-radius:5px;text-decoration:none;font-weight:bold;">'
            ' Gen HRMS Token</a>'
            '<a href="{}" '
            'style="background-color:#f59e0b;color:white;padding:4px 10px;border-radius:5px;text-decoration:none;font-weight:bold;">'
            ' Gen Leave Token</a>'
            '</div>',
            obj.id, token_url, leave_token_url
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
# Recruitment Models Admin
# ─────────────────────────────


@admin.register(CalendarEvent)
class CalendarEventAdmin(admin.ModelAdmin):
    list_display = ("title", "date_time", "duration_minutes", "organization")
    list_filter = ("organization", "date_time")
    search_fields = ("title", "location_link")
    date_hierarchy = "date_time"
    filter_horizontal = ("participants",)





@admin.register(OrganizationLeavePolicy)
class OrganizationLeavePolicyAdmin(admin.ModelAdmin):
    list_display = ("organization", "year", "leave_type", "default_allocated")
    list_filter = ("organization", "year", "leave_type")

@admin.register(LeaveBalance)
class LeaveBalanceAdmin(admin.ModelAdmin):
    list_display = ("employee", "organization", "year", "leave_type", "total_allocated", "used", "remaining")
    list_filter = ("organization", "year", "leave_type")
    search_fields = ("employee__username", "employee__name")

@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = ("employee", "organization", "leave_type", "start_date", "end_date", "status", "is_deducted")
    list_filter = ("status", "organization")

@admin.register(HRMSSystemConfig)
class HRMSSystemConfigAdmin(admin.ModelAdmin):
    list_display = ("organization", "hrms_type", "is_active", "edit_token", "edit_token_expires_at")
    list_filter = ("hrms_type", "is_active")
    search_fields = ("organization__name", "edit_token")
    readonly_fields = ("edit_token", "edit_token_expires_at")
    actions = ["generate_new_edit_token"]

    def generate_new_edit_token(self, request, queryset):
        for config in queryset:
            token = config.generate_edit_token()
        self.message_user(request, f"Generated new edit tokens for {queryset.count()} organization(s).")
    generate_new_edit_token.short_description = "Generate fresh 24h Edit Token"

@admin.register(LeaveSystemConfig)
class LeaveSystemConfigAdmin(admin.ModelAdmin):
    list_display = ("organization", "edit_token", "edit_token_expires_at")
    search_fields = ("organization__name", "edit_token")
    readonly_fields = ("edit_token", "edit_token_expires_at")
    actions = ["generate_new_edit_token"]

    def generate_new_edit_token(self, request, queryset):
        for config in queryset:
            token = config.generate_edit_token()
        self.message_user(request, f"Generated new Leave edit tokens for {queryset.count()} organization(s).")
    generate_new_edit_token.short_description = "Generate fresh 24h Edit Token"

# ─────────────────────────────
# App Log Admin (read-only viewer)
# ─────────────────────────────
LEVEL_COLOURS = {
    "DEBUG":    "#6b7280",
    "INFO":     "#3b82f6",
    "WARNING":  "#f59e0b",
    "ERROR":    "#ef4444",
    "CRITICAL": "#7c3aed",
}

@admin.register(AppLog)
class AppLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "coloured_level", "logger_name", "short_message", "module", "task_id")
    list_filter = ("level", "logger_name")
    search_fields = ("message", "module", "func_name", "task_id", "exc_text")
    date_hierarchy = "created_at"
    readonly_fields = (
        "created_at", "level", "logger_name", "message",
        "module", "func_name", "line_no", "task_id", "exc_text",
    )
    list_per_page = 100
    ordering = ("-created_at",)

    # Disable add / change — logs are read-only
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def coloured_level(self, obj):
        colour = LEVEL_COLOURS.get(obj.level, "#6b7280")
        return format_html(
            '<span style="color:{};font-weight:bold;">{}</span>',
            colour,
            obj.level,
        )
    coloured_level.short_description = "Level"
    coloured_level.admin_order_field = "level"

    def short_message(self, obj):
        return obj.message[:120] + ("…" if len(obj.message) > 120 else "")
    short_message.short_description = "Message"


# ─────────────────────────────
# Customize Admin Branding
# ─────────────────────────────
admin.site.site_header = "Harvey Admin Panel"
admin.site.index_title = "Harvey Administration"
admin.site.site_title = "Harvey Admin"
