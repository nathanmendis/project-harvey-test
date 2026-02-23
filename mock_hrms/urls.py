from django.urls import path
from . import views

urlpatterns = [
    path('v1/employees/', views.list_employees),

    path('v1/employees/<str:employee_id>/leave-balance/', views.employee_leave_balance),

    path('v1/employees/<str:employee_id>/', views.employee_detail),

    path('v1/candidates/', views.list_candidates),
    path('v1/candidates/<str:candidate_id>/', views.candidate_detail),
    path('v1/candidates/create/', views.create_candidate),

    path('v1/job-requisitions/', views.list_job_requisitions),
    path('v1/job-requisitions/<str:requisition_id>/', views.job_requisition_detail),

    path('v1/interviews/', views.list_interviews),
    path('v1/interviews/schedule/', views.schedule_interview),

    path('v1/leave-requests/', views.list_leave_requests),
    path('v1/leave-requests/create/', views.create_leave_request),

    path('v1/departments/', views.list_departments),
]