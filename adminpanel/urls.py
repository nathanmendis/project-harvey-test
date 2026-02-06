from django.urls import path
from . import views

urlpatterns = [
    path("dashboard/", views.admin_dashboard, name="admin_dashboard"),
    path("invite/", views.invite_user, name="invite_user"),
    path("add-employee/", views.add_employee, name="add_employee"),
    path("manage-employees/", views.manage_employees, name="manage_employees"),
    path("remove-employee/<int:user_id>/", views.remove_employee, name="remove_employee"),
    path("toggle-chat-access/<int:user_id>/", views.toggle_chat_access, name="toggle_chat_access"),
    path("add-org-admin/", views.add_org_admin, name="add_org_admin"),
    path("manage-org-admins/", views.manage_org_admins, name="manage_org_admins"),
    path("toggle-admin/<int:user_id>/", views.toggle_admin_role, name="toggle_admin_role"),
    path("search-employee/", views.search_employee, name="search_employee"), 
    
    # Policy Management
    path("policies/", views.manage_policies, name="manage_policies"),
    path("policies/add/", views.add_policy, name="add_policy"),
    path("policies/reindex/<uuid:policy_id>/", views.reindex_policy, name="reindex_policy"),
    path("policies/delete/<uuid:policy_id>/", views.delete_policy, name="delete_policy"),
    
    # Recruitment Management
    path("recruitment/", views.recruitment_dashboard, name="recruitment_dashboard"),
    path("recruitment/candidates/", views.candidates, name="candidates"),
    path("recruitment/candidates/add/", views.add_candidate, name="add_candidate"),
    path("recruitment/candidates/<int:candidate_id>/", views.candidate_detail, name="candidate_detail"),
    path("recruitment/jobs/", views.jobs, name="jobs"),
    path("recruitment/jobs/add/", views.add_job, name="add_job"),
    path("recruitment/jobs/<int:job_id>/", views.job_detail, name="job_detail"),
    path("recruitment/interviews/", views.interviews, name="interviews"),
    path("recruitment/interviews/<int:interview_id>/", views.interview_detail, name="interview_detail"),
    
    # Leave Management
    path("leaves/", views.leaves, name="leaves"),
    path("leaves/<int:leave_id>/", views.leave_detail, name="leave_detail"),
    path("leaves/<int:leave_id>/approve/", views.approve_leave, name="approve_leave"),
    
    # Org Settings
    path("settings/", views.org_settings, name="org_settings"),
]
