from django.urls import path
from . import views

urlpatterns = [
    path("dashboard/", views.admin_dashboard, name="admin_dashboard"),
    path("add-employee/", views.add_employee, name="add_employee"),
    path("manage-employees/", views.manage_employees, name="manage_employees"),
    path("remove-employee/<int:user_id>/", views.remove_employee, name="remove_employee"),
    path("toggle-chat-access/<int:user_id>/", views.toggle_chat_access, name="toggle_chat_access"),
]
