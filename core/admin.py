from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.contrib.auth.hashers import make_password
from .models import Organization, User, Policy, PolicyChunk
from .models.recruitment import (
    Candidate, JobRole, Interview, EmailLog, 
    CalendarEvent, LeaveRequest, CandidateJobScore
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
# Recruitment Models Admin
# ─────────────────────────────
@admin.register(Candidate)
class CandidateAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "organization", "status", "source")
    list_filter = ("status", "organization", "source")
    search_fields = ("name", "email", "skills")
    readonly_fields = ("parsed_data",)


@admin.register(JobRole)
class JobRoleAdmin(admin.ModelAdmin):
    list_display = ("title", "department", "organization")
    list_filter = ("department", "organization")
    search_fields = ("title", "description", "requirements")


@admin.register(Interview)
class InterviewAdmin(admin.ModelAdmin):
    list_display = ("candidate", "interviewer", "date_time", "status", "organization")
    list_filter = ("status", "organization", "date_time")
    search_fields = ("candidate__name", "interviewer__username")
    date_hierarchy = "date_time"


@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    list_display = ("recipient_email", "subject", "sent_time", "status", "organization")
    list_filter = ("status", "organization", "sent_time")
    search_fields = ("recipient_email", "subject", "body")
    date_hierarchy = "sent_time"
    readonly_fields = ("sent_time",)


@admin.register(CalendarEvent)
class CalendarEventAdmin(admin.ModelAdmin):
    list_display = ("title", "date_time", "duration_minutes", "organization")
    list_filter = ("organization", "date_time")
    search_fields = ("title", "location_link")
    date_hierarchy = "date_time"
    filter_horizontal = ("participants",)


@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = ("employee", "leave_type", "start_date", "end_date", "status", "organization")
    list_filter = ("status", "leave_type", "organization")
    search_fields = ("employee__username", "employee__name")
    date_hierarchy = "start_date"


@admin.register(CandidateJobScore)
class CandidateJobScoreAdmin(admin.ModelAdmin):
    list_display = ("candidate", "job_role", "score", "created_at")
    list_filter = ("job_role", "created_at")
    search_fields = ("candidate__name", "job_role__title")
    readonly_fields = ("created_at",)


# ─────────────────────────────
# Customize Admin Branding
# ─────────────────────────────
admin.site.site_header = "Harvey Admin Panel"
admin.site.index_title = "Harvey Administration"
admin.site.site_title = "Harvey Admin"

