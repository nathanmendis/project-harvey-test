from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json

def candidate_detail(request, candidate_id):
    return JsonResponse({
        "id": candidate_id,
        "candidate_id": candidate_id,
        "first_name": "Alice",
        "last_name": "Johnson",
        "email": "alice.j@email.com",
        "phone": "+91-9123456789",
        "current_stage": "technical_interview",
        "applied_for_job_id": "JOB001",
        "applied_for_job_title": "Senior Backend Engineer",
        "source": "linkedin",
        "application_date": "2026-01-20",
        "status": "active",
        "resume_url": "https://hrms.company.com/resumes/CAND001.pdf",
        "linkedin_url": "https://linkedin.com/in/alicejohnson",
        "skills": ["Python", "Django", "PostgreSQL", "Docker"],
        "experience_years": 6,
        "current_company": "Tech Corp",
        "current_title": "Backend Engineer",
        "education": [
            {
                "degree": "B.Tech",
                "field": "Computer Science",
                "institution": "IIT Delhi",
                "year": 2018
            }
        ]
    })

def job_requisition_detail(request, requisition_id):
    return JsonResponse({
        "id": requisition_id,
        "requisition_id": "REQ-2026-001",
        "title": "Senior Backend Engineer",
        "department": "Engineering",
        "hiring_manager_id": "EMP100",
        "hiring_manager_name": "Jane Smith",
        "status": "open",
        "headcount": 2,
        "filled_positions": 0,
        "location": "Bangalore",
        "job_type": "full_time",
        "description": "We are looking for an experienced backend engineer...",
        "requirements": [
            "5+ years of Python experience",
            "Strong Django knowledge",
            "Experience with microservices"
        ],
        "nice_to_have": [
            "ML/AI background"
        ],
        "salary_range": {
            "min": 2000000,
            "max": 3500000,
            "currency": "INR"
        },
        "created_date": "2026-01-15",
        "target_hire_date": "2026-03-01"
    })
# -------------------------
# EMPLOYEES
# -------------------------

def list_employees(request):
    return JsonResponse({
        "data": [
            {
                "id": "EMP001",
                "first_name": "John",
                "last_name": "Doe",
                "email": "john.doe@company.com",
                "department": "Engineering",
                "status": "active"
            },
            {
                "id": "EMP002",
                "first_name": "Jane",
                "last_name": "Smith",
                "email": "jane.smith@company.com",
                "department": "HR",
                "status": "active"
            }
        ],
        "total": 2,
        "page": 1,
        "page_size": 50
    })


def employee_detail(request, employee_id):
    return JsonResponse({
        "id": employee_id,
        "first_name": "John",
        "last_name": "Doe",
        "email": "john.doe@company.com",
        "department": "Engineering",
        "status": "active"
    })


# -------------------------
# CANDIDATES
# -------------------------

def list_candidates(request):
    return JsonResponse({
        "data": [
            {
                "id": "CAND001",
                "first_name": "Alice",
                "last_name": "Brown",
                "email": "alice@email.com",
                "status": "applied"
            }
        ],
        "total": 1
    })


@csrf_exempt
def create_candidate(request):
    if request.method == "POST":
        body = json.loads(request.body)
        return JsonResponse({
            "id": "CAND002",
            "candidate_id": "CAND002",
            "status": "created",
            "message": "Candidate successfully added to the system"
        })
    return JsonResponse({"error": "Invalid method"}, status=400)


# -------------------------
# JOB REQUISITIONS
# -------------------------

def list_job_requisitions(request):
    return JsonResponse({
        "data": [
            {
                "id": "JOB001",
                "title": "Software Engineer",
                "department": "Engineering",
                "status": "open"
            }
        ]
    })


# -------------------------
# INTERVIEWS
# -------------------------

def list_interviews(request):
    return JsonResponse({
        "data": [
            {
                "id": "INT001",
                "candidate_id": "CAND001",
                "interviewer": "John Doe",
                "date": "2026-02-25",
                "status": "scheduled"
            }
        ]
    })


@csrf_exempt
def schedule_interview(request):
    if request.method == "POST":
        return JsonResponse({
            "id": "INT002",
            "status": "scheduled",
            "message": "Interview successfully scheduled"
        })
    return JsonResponse({"error": "Invalid method"}, status=400)

def list_leave_requests(request):
    return JsonResponse({
        "data": [
            {
                "id": "LEAVE001",
                "leave_request_id": "LEAVE001",
                "employee_id": "EMP001",
                "employee_name": "John Doe",
                "leave_type": "annual",
                "start_date": "2026-03-01",
                "end_date": "2026-03-05",
                "total_days": 5,
                "status": "pending",
                "applied_date": "2026-02-10",
                "reason": "Family vacation"
            }
        ],
        "total": 1,
        "page": 1,
        "page_size": 20
    })

@csrf_exempt
def create_leave_request(request):
    if request.method == "POST":
        return JsonResponse({
            "id": "LEAVE002",
            "leave_request_id": "LEAVE002",
            "status": "pending",
            "message": "Leave request submitted successfully"
        }, status=201)

    return JsonResponse({"error": "Invalid method"}, status=400)

def list_departments(request):
    return JsonResponse({
        "data": [
            {
                "id": "DEPT001",
                "department_id": "DEPT001",
                "name": "Engineering",
                "head_id": "EMP100",
                "head_name": "Jane Smith",
                "employee_count": 45,
                "location": "Bangalore"
            },
            {
                "id": "DEPT002",
                "department_id": "DEPT002",
                "name": "Product",
                "head_id": "EMP101",
                "head_name": "Mark Davis",
                "employee_count": 12,
                "location": "Bangalore"
            }
        ]
    })

def employee_leave_balance(request, employee_id):
    return JsonResponse({
        "employee_id": employee_id,
        "leave_balances": [
            {
                "leave_type": "annual",
                "total_allocated": 20,
                "used": 5,
                "pending": 2,
                "available": 13
            },
            {
                "leave_type": "sick",
                "total_allocated": 10,
                "used": 2,
                "pending": 0,
                "available": 8
            }
        ],
        "year": 2026
    })
