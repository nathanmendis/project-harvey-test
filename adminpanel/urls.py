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
    
    # Org Settings
    path("settings/", views.org_settings, name="org_settings"),
]
