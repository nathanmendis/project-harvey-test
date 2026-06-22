from datetime import timedelta
from core.models import Candidate, JobRole, Interview, EmailLog, CalendarEvent, LeaveRequest, CandidateJobScore
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from django.db.models import Q
from django.core.paginator import Paginator
from adminpanel.forms import CandidateForm, JobForm, InterviewForm
from .utils import is_admin_manager_hr , is_org_admin
from django.contrib import messages
from django.views.decorators.clickjacking import xframe_options_sameorigin

@login_required
@user_passes_test(is_admin_manager_hr)
def recruitment_dashboard(request):
    """View to display recruitment dashboard."""
    org = request.user.organization
    
    return render(request, 'recruitment/dashboard.html', {
        'org': org,
    })

@login_required
@user_passes_test(is_admin_manager_hr)
def candidates(request):
    """View to display list of candidates."""
    org = request.user.organization
    query = request.GET.get('q', '').strip()
    
    candidates_list = Candidate.objects.filter(organization=org).order_by('-id')
    
    if query:
        candidates_list = candidates_list.filter(
            Q(name__icontains=query) |
            Q(email__icontains=query) |
            Q(phone__icontains=query)
        )
        
    paginator = Paginator(candidates_list, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'recruitment/candidates.html', {
        'org': org,
        'candidates': page_obj,
        'page_obj': page_obj,
        'paginator': paginator,
    })

@login_required
@user_passes_test(is_admin_manager_hr)
def jobs(request):
    """View to display list of job roles."""
    org = request.user.organization
    query = request.GET.get('q', '').strip()
    
    jobs_list = JobRole.objects.filter(organization=org).order_by('-id')
    
    if query:
        jobs_list = jobs_list.filter(
            Q(title__icontains=query) |
            Q(status__icontains=query)
        )
        
    paginator = Paginator(jobs_list, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'recruitment/jobs.html', {
        'org': org,
        'jobs': page_obj,
        'page_obj': page_obj,
        'paginator': paginator,
    })

@login_required
@user_passes_test(is_admin_manager_hr)
def interviews(request):
    """View to display list of interviews."""
    from django.utils import timezone
    timezone.activate('Asia/Kolkata')
    
    org = request.user.organization
    query = request.GET.get('q', '').strip()
    
    interviews_list = Interview.objects.filter(organization=org).select_related('candidate', 'interviewer').order_by('-id')
    
    if query:
        interviews_list = interviews_list.filter(
            Q(candidate__name__icontains=query) |
            Q(interviewer__name__icontains=query) |
            Q(status__icontains=query)
        )
        
    paginator = Paginator(interviews_list, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'recruitment/interviews.html', {
        'org': org,
        'interviews': page_obj,
        'page_obj': page_obj,
        'paginator': paginator,
    })




@login_required
@user_passes_test(is_admin_manager_hr)
def candidate_detail(request, candidate_id):
    """View to display candidate details."""
    org = request.user.organization
    candidate = get_object_or_404(Candidate, id=candidate_id, organization=org)
    
    return render(request, 'recruitment/candidate_detail.html', {
        'org': org,
        'candidate': candidate,
    })

@login_required
@user_passes_test(is_admin_manager_hr)
def job_detail(request, job_id):
    """View to display or edit job details in place."""
    org = request.user.organization
    job = get_object_or_404(JobRole, id=job_id, organization=org)
    
    edit_mode = request.GET.get('edit') == 'true'
    form = None
    
    if request.method == "POST":
        form = JobForm(request.POST, instance=job)
        if form.is_valid():
            form.save()
            messages.success(request, "Job updated successfully.")
            return redirect('job_detail', job_id=job.id)
        else:
            edit_mode = True  # Remain in edit mode to show form errors
    else:
        if edit_mode:
            form = JobForm(instance=job)
            
    return render(request, 'recruitment/job_detail.html', {
        'org': org,
        'job': job,
        'edit_mode': edit_mode,
        'form': form,
    })

@login_required
@user_passes_test(is_admin_manager_hr)
def interview_detail(request, interview_id):
    """View to display interview details."""
    org = request.user.organization
    interview = get_object_or_404(Interview, id=interview_id, organization=org)
    
    return render(request, 'recruitment/interview_detail.html', {
        'org': org,
        'interview': interview,
    })

@login_required
@user_passes_test(is_admin_manager_hr)
def email_detail(request, email_id):
    """View to display email details."""
    org = request.user.organization
    email = get_object_or_404(EmailLog, id=email_id, organization=org)
    
    return render(request, 'recruitment/email_detail.html', {
        'org': org,
        'email': email,
    })

@login_required
@user_passes_test(is_admin_manager_hr)
def calendar_event_detail(request, event_id):
    """View to display calendar event details."""
    org = request.user.organization
    event = get_object_or_404(CalendarEvent, id=event_id, organization=org)
    
    return render(request, 'recruitment/calendar_event_detail.html', {
        'org': org,
        'event': event,
    })


@login_required
@user_passes_test(is_admin_manager_hr)
def candidate_job_score_detail(request, score_id):
    """View to display candidate job score details."""
    org = request.user.organization
    score = get_object_or_404(CandidateJobScore, id=score_id, organization=org)
    
    return render(request, 'recruitment/candidate_job_score_detail.html', {
        'org': org,
        'score': score,
    })

@login_required
@user_passes_test(is_admin_manager_hr)
def add_candidate(request):
    """View to add a new candidate."""
    org = request.user.organization
    
    if request.method == "POST":
        form = CandidateForm(request.POST, request.FILES)
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
@user_passes_test(is_admin_manager_hr)
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

@login_required
@user_passes_test(is_admin_manager_hr)
def search_candidate(request):
    """Search candidates by name, email, or phone."""
    query = request.GET.get("q", "").strip()
    org = request.user.organization

    if not query:
        return JsonResponse({"results": []})

    candidates = Candidate.objects.filter(
        organization=org
    ).filter(
        Q(name__icontains=query) |
        Q(email__icontains=query) |
        Q(phone__icontains=query)
    ).values("id", "name", "email", "phone", "source", "status")

    return JsonResponse({"results": list(candidates)})


@login_required
@user_passes_test(is_admin_manager_hr)
def delete_candidate(request, candidate_id):
    """View to delete a candidate."""
    org = request.user.organization
    candidate = get_object_or_404(Candidate, id=candidate_id, organization=org)
    
    # Ideally this would be a POST request for security
    candidate.delete()
    from django.contrib import messages
    messages.success(request, f"Candidate {candidate.name} deleted successfully.")
    return redirect('candidates')


@login_required
@user_passes_test(is_admin_manager_hr)
def schedule_interview(request):
    """View to schedule a new interview."""
    from django.utils import timezone
    timezone.activate('Asia/Kolkata') # Force IST for form parsing and display
    
    org = request.user.organization
    candidate_id = request.GET.get('candidate_id')
    initial_data = {}
    
    if candidate_id:
        initial_data['candidate'] = get_object_or_404(Candidate, id=candidate_id, organization=org)
    
    if request.method == "POST":
        form = InterviewForm(request.POST)
        if form.is_valid():
            interview = form.save(commit=False)
            interview.organization = org
            interview.save()
            
            # Localize time for display and sync (Asia/Kolkata)
            import pytz
            tz_name = 'Asia/Kolkata'
            tz_obj = pytz.timezone(tz_name)
            local_dt = interview.date_time.astimezone(tz_obj)

            # 1. Handle Google Calendar & Meet Integration
            meet_link = None
            if org.google_refresh_token:
                try:
                    from integrations.google.calendar import CalendarService
                    cal = CalendarService(user=request.user)
                    
                    # Replicate TOOL Logic: Naive ISO string + explicit TZ context
                    naive_dt = local_dt.replace(tzinfo=None)
                    start_time_str = naive_dt.strftime("%Y-%m-%dT%H:%M:%S")
                    end_time_str = (naive_dt + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S")
                    
                    attendees = [interview.candidate.email, interview.interviewer.email]
                    
                    event = cal.create_event(
                        title=f"Interview: {interview.candidate.name} x {org.name}",
                        start_time=start_time_str,
                        end_time=end_time_str,
                        attendees=attendees,
                        description=interview.description,
                        timezone=tz_name,
                        use_meet=(interview.interview_type == 'online')
                    )
                    
                    meet_link = event.get('hangoutLink')
                    if meet_link and interview.interview_type == 'online':
                        interview.location = meet_link # Store Meet link in location
                        interview.save()
                        messages.success(request, "Google Meet link generated and synced to calendar.")
                    else:
                        messages.success(request, "Interview synced to Google Calendar.")
                        
                except Exception as e:
                    messages.warning(request, f"Stored locally, but failed to sync Calendar: {str(e)}")

            # 2. Handle Automated Emailing
            if org.google_refresh_token:
                try:
                    from integrations.google.gmail import GmailService
                    gmail = GmailService(user=request.user)
                    
                    location_str = meet_link if interview.interview_type == 'online' else interview.location
                    subject = f"Interview Invitation: {interview.candidate.name} x {org.name}"
                    
                    # Prepare Context for HTML Template
                    context = {
                        'candidate_name': interview.candidate.name,
                        'org_name': org.name,
                        'job_title': 'Member of Technical Staff', # Fallback or dynamic
                        'interviewer_name': interview.interviewer.username,
                        'interview_time': local_dt.strftime('%B %d, %Y at %I:%M %p'),
                        'location': location_str or 'TBD',
                        'meet_link': meet_link if interview.interview_type == 'online' else None,
                        'description': interview.description,
                    }
                    
                    from django.template.loader import render_to_string
                    from django.utils.html import strip_tags
                    
                    html_content = render_to_string('emails/interview_invite.html', context)
                    text_content = strip_tags(html_content)
                    
                    # Send to Candidate (Standard HTML)
                    gmail.send_email(interview.candidate.email, subject, text_content, html_content=html_content)
                    
                    # Send to Interviewer (With Resume Attachment + HTML)
                    resume_path = interview.candidate.resume_file.path if interview.candidate.resume_file else None
                    gmail.send_email(interview.interviewer.email, f"[Internal] {subject}", text_content, html_content=html_content, attachment_path=resume_path)
                    
                    messages.success(request, "Premium confirmation emails sent successfully.")
                except Exception as e:
                    messages.warning(request, f"Emails failed: {str(e)}")
            
            return redirect('interviews')
    else:
        form = InterviewForm(initial=initial_data)
        form.fields['candidate'].queryset = Candidate.objects.filter(organization=org)
        from core.models.organization import User
        form.fields['interviewer'].queryset = User.objects.filter(organization=org)
        
    return render(request, 'recruitment/schedule_interview.html', {
        'org': org,
        'form': form,
    })


@login_required
@user_passes_test(is_admin_manager_hr)
def cancel_interview(request, interview_id):
    """View to cancel an interview."""
    org = request.user.organization
    interview = get_object_or_404(Interview, id=interview_id, organization=org)
    
    interview.status = 'cancelled'
    interview.save()
    
    # Optional: Send cancellation email
    if org.google_refresh_token:
        try:
            from integrations.google.gmail import GmailService
            gmail = GmailService(user=request.user)
            subject = f"Interview CANCELLED: {interview.candidate.name} x {org.name}"
            body = f"The interview for {interview.candidate.name} scheduled for {interview.date_time.strftime('%B %d, %Y')} has been cancelled."
            gmail.send_email(interview.candidate.email, subject, body)
            gmail.send_email(interview.interviewer.email, subject, body)
        except:
            pass

    messages.success(request, f"Interview with {interview.candidate.name} has been cancelled.")
    return redirect('interviews')


@login_required
@user_passes_test(is_admin_manager_hr)
def update_interview_status(request, interview_id):
    """View to update the status of an interview via POST."""
    if request.method == "POST":
        org = request.user.organization
        interview = get_object_or_404(Interview, id=interview_id, organization=org)
        new_status = request.POST.get('status')
        
        if new_status in dict(Interview.STATUS_CHOICES):
            interview.status = new_status
            interview.save()
            messages.success(request, f"Interview status updated to {interview.get_status_display()}.")
        else:
            messages.error(request, "Invalid status.")
            
    return redirect('interviews')


@login_required
@user_passes_test(is_admin_manager_hr)
@xframe_options_sameorigin
def view_resume(request, candidate_id):
    """Securely view a candidate resume."""
    org = request.user.organization
    candidate = get_object_or_404(Candidate, id=candidate_id, organization=org)
    
    return render(request, "recruitment/view_resume.html", {
        "candidate": candidate,
        "org": org
    })


@login_required
@user_passes_test(is_admin_manager_hr)
def mark_job_filled(request, job_id):
    """Mark a job role as filled."""
    org = request.user.organization
    job = get_object_or_404(JobRole, id=job_id, organization=org)
    job.is_filled = True
    job.save()
    messages.success(request, f"Job '{job.title}' has been marked as filled.")
    return redirect('jobs')


@login_required
@user_passes_test(is_admin_manager_hr)
def delete_job(request, job_id):
    """Delete a job role."""
    org = request.user.organization
    job = get_object_or_404(JobRole, id=job_id, organization=org)
    job_title = job.title
    job.delete()
    messages.success(request, f"Job '{job_title}' deleted successfully.")
    return redirect('jobs')
