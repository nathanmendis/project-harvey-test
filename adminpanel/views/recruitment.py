from core.models import Candidate, JobRole, Interview, EmailLog, CalendarEvent, LeaveRequest, CandidateJobScore
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from adminpanel.forms import CandidateForm, JobForm
from .utils import is_org_admin

@login_required
@user_passes_test(is_org_admin)
def recruitment_dashboard(request):
    """View to display recruitment dashboard."""
    org = request.user.organization
    
    return render(request, 'recruitment/dashboard.html', {
        'org': org,
    })

@login_required
@user_passes_test(is_org_admin)
def candidates(request):
    """View to display list of candidates."""
    org = request.user.organization
    candidates = Candidate.objects.filter(organization=org)
    
    return render(request, 'recruitment/candidates.html', {
        'org': org,
        'candidates': candidates,
    })

@login_required
@user_passes_test(is_org_admin)
def jobs(request):
    """View to display list of job roles."""
    org = request.user.organization
    jobs = JobRole.objects.filter(organization=org)
    
    return render(request, 'recruitment/jobs.html', {
        'org': org,
        'jobs': jobs,
    })

@login_required
@user_passes_test(is_org_admin)
def interviews(request):
    """View to display list of interviews."""
    org = request.user.organization
    interviews = Interview.objects.filter(organization=org)
    
    return render(request, 'recruitment/interviews.html', {
        'org': org,
        'interviews': interviews,
    })




@login_required
@user_passes_test(is_org_admin)
def candidate_detail(request, candidate_id):
    """View to display candidate details."""
    org = request.user.organization
    candidate = get_object_or_404(Candidate, id=candidate_id, organization=org)
    
    return render(request, 'recruitment/candidate_detail.html', {
        'org': org,
        'candidate': candidate,
    })

@login_required
@user_passes_test(is_org_admin)
def job_detail(request, job_id):
    """View to display job details."""
    org = request.user.organization
    job = get_object_or_404(JobRole, id=job_id, organization=org)
    
    return render(request, 'recruitment/job_detail.html', {
        'org': org,
        'job': job,
    })

@login_required
@user_passes_test(is_org_admin)
def interview_detail(request, interview_id):
    """View to display interview details."""
    org = request.user.organization
    interview = get_object_or_404(Interview, id=interview_id, organization=org)
    
    return render(request, 'recruitment/interview_detail.html', {
        'org': org,
        'interview': interview,
    })

@login_required
@user_passes_test(is_org_admin)
def email_detail(request, email_id):
    """View to display email details."""
    org = request.user.organization
    email = get_object_or_404(EmailLog, id=email_id, organization=org)
    
    return render(request, 'recruitment/email_detail.html', {
        'org': org,
        'email': email,
    })

@login_required
@user_passes_test(is_org_admin)
def calendar_event_detail(request, event_id):
    """View to display calendar event details."""
    org = request.user.organization
    event = get_object_or_404(CalendarEvent, id=event_id, organization=org)
    
    return render(request, 'recruitment/calendar_event_detail.html', {
        'org': org,
        'event': event,
    })


@login_required
@user_passes_test(is_org_admin)
def candidate_job_score_detail(request, score_id):
    """View to display candidate job score details."""
    org = request.user.organization
    score = get_object_or_404(CandidateJobScore, id=score_id, organization=org)
    
    return render(request, 'recruitment/candidate_job_score_detail.html', {
        'org': org,
        'score': score,
    })

@login_required
@user_passes_test(is_org_admin)
def add_candidate(request):
    """View to add a new candidate."""
    org = request.user.organization
    
    if request.method == "POST":
        form = CandidateForm(request.POST)
        if form.is_valid():
            candidate = form.save(commit=False)
            candidate.organization = org
            candidate.save()
            messages.success(request, "Candidate added successfully.")
            return redirect('candidates')
    else:
        form = CandidateForm()
    
    return render(request, 'recruitment/add_candidate.html', {
        'org': org,
        'form': form,
    })

@login_required
@user_passes_test(is_org_admin)
def add_job(request):
    """View to add a new job role."""
    org = request.user.organization
    
    if request.method == "POST":
        form = JobForm(request.POST)
        if form.is_valid():
            job = form.save(commit=False)
            job.organization = org
            job.save()
            messages.success(request, "Job added successfully.")
            return redirect('jobs')
    else:
        form = JobForm()
    
    return render(request, 'recruitment/add_job.html', {
        'org': org,
        'form': form,
    })
