"""
Celery tasks for the core app.

Candidate and JobRole vector-index maintenance is done here (periodic task
every 2 hours), instead of via Django signals, so that:
  - A save() on a Candidate/JobRole doesn't block or leak threads.
  - The RAG admin dashboard can also manually trigger these tasks.
"""

import logging
from celery import shared_task
from django.db import transaction

logger = logging.getLogger("harvey")


# ──────────────────────────────────────────────────────────────────────────────
# Periodic tasks (candidates + jobs)

@shared_task(bind=True, max_retries=2, default_retry_delay=60)
def index_candidates_and_jobs(self):
    """
    Periodic task: re-index ALL candidates and job roles for every organisation.
    Runs every 2 hours (configured in project_harvey/celery.py beat_schedule).

    Returns a summary dict so the Celery result backend can log it.
    """
    from core.models.recruitment import Candidate, JobRole
    from core.ai.rag.model_indexer import ModelIndexer

    indexer = ModelIndexer()

    candidate_ok = candidate_fail = 0
    job_ok = job_fail = 0

    try:
        # ---- Candidates ----
        for candidate in Candidate.objects.all():
            try:
                indexer.index_candidate(candidate.id)
                candidate_ok += 1
            except Exception as exc:
                candidate_fail += 1
                logger.warning("Failed to index candidate %s: %s", candidate.id, exc)

        # ---- Jobs ----
        for job in JobRole.objects.all():
            try:
                indexer.index_job_role(job.id)
                job_ok += 1
            except Exception as exc:
                job_fail += 1
                logger.warning("Failed to index job %s: %s", job.id, exc)

        summary = {
            "candidates_indexed": candidate_ok,
            "candidates_failed": candidate_fail,
            "jobs_indexed": job_ok,
            "jobs_failed": job_fail,
        }
        logger.info("RAG periodic index complete: %s", summary)
        return summary

    except Exception as exc:
        logger.error("RAG periodic index task crashed: %s", exc)
        raise self.retry(exc=exc)


# ──────────────────────────────────────────────────────────────────────────────
# On-demand tasks (triggered from the RAG admin dashboard)

@shared_task(bind=True, max_retries=2, default_retry_delay=30)
def reindex_all_candidates_task(self, organization_id=None):
    """
    Reindex all candidates for a given org (or all orgs if None).
    Triggered from the RAG admin dashboard.
    """
    from core.models.recruitment import Candidate
    from core.ai.rag.model_indexer import ModelIndexer

    indexer = ModelIndexer()
    qs = Candidate.objects.all()
    if organization_id:
        qs = qs.filter(organization_id=organization_id)

    ok = fail = 0
    for candidate in qs:
        try:
            indexer.index_candidate(candidate.id)
            ok += 1
        except Exception as exc:
            fail += 1
            logger.warning("Failed to index candidate %s: %s", candidate.id, exc)

    logger.info("Admin reindex candidates: ok=%s fail=%s", ok, fail)
    return {"indexed": ok, "failed": fail}


@shared_task(bind=True, max_retries=2, default_retry_delay=30)
def reindex_all_jobs_task(self, organization_id=None):
    """
    Reindex all job roles for a given org (or all orgs if None).
    Triggered from the RAG admin dashboard.
    """
    from core.models.recruitment import JobRole
    from core.ai.rag.model_indexer import ModelIndexer

    indexer = ModelIndexer()
    qs = JobRole.objects.all()
    if organization_id:
        qs = qs.filter(organization_id=organization_id)

    ok = fail = 0
    for job in qs:
        try:
            indexer.index_job_role(job.id)
            ok += 1
        except Exception as exc:
            fail += 1
            logger.warning("Failed to index job %s: %s", job.id, exc)

    logger.info("Admin reindex jobs: ok=%s fail=%s", ok, fail)
    return {"indexed": ok, "failed": fail}


@shared_task(bind=True, max_retries=2, default_retry_delay=30)
def reindex_all_policies_task(self, organization_id=None):
    """
    Reindex all policies for a given org (or all orgs if None).
    Triggered from the RAG admin dashboard.
    """
    from core.models.policy import Policy
    from core.ai.rag.policy_indexer import PolicyIndexer

    indexer = PolicyIndexer()
    qs = Policy.objects.all()
    if organization_id:
        qs = qs.filter(created_by__organization_id=organization_id)

    ok = fail = 0
    for policy in qs:
        try:
            success = indexer.index_policy(policy.id)
            if success:
                ok += 1
            else:
                fail += 1
        except Exception as exc:
            fail += 1
            logger.warning("Failed to index policy %s: %s", policy.id, exc)

    logger.info("Admin reindex policies: ok=%s fail=%s", ok, fail)
    return {"indexed": ok, "failed": fail}

@shared_task(bind=True, max_retries=2, default_retry_delay=30)
def allocate_leave_balances_task(self, policy_id):
    """
    Background task to allocate or update LeaveBalances for all employees
    when an OrganizationLeavePolicy is created or updated.
    """
    from core.models.leaves import OrganizationLeavePolicy, LeaveBalance
    from core.models.organization import User

    try:
        policy = OrganizationLeavePolicy.objects.get(id=policy_id)
    except OrganizationLeavePolicy.DoesNotExist:
        logger.warning("Leave policy %s no longer exists. Aborting allocation.", policy_id)
        return {"status": "aborted"}

    employees = User.objects.filter(organization=policy.organization, is_active=True)
    alloc_count = 0

    for employee in employees:
        balance, balance_created = LeaveBalance.objects.get_or_create(
            employee=employee,
            organization=policy.organization,
            year=policy.year,
            leave_type=policy.leave_type,
            defaults={'total_allocated': policy.default_allocated, 'used': 0.0}
        )
        
        if balance_created:
            alloc_count += 1
            # 1. Provide carryover natively from the prior year
            last_year_balance = LeaveBalance.objects.filter(
                employee=employee,
                organization=policy.organization,
                year=policy.year - 1,
                leave_type=policy.leave_type
            ).first()
            
            if last_year_balance and last_year_balance.remaining > 0:
                balance.total_allocated += last_year_balance.remaining
                balance.save()

    logger.info("Leave allocation complete for policy %s. Provisioned %s employee accounts.", policy_id, alloc_count)
    return {"provisioned": alloc_count}


@shared_task(bind=True, max_retries=1)
def send_daily_manager_digest(self):
    """
    Sends a daily email to managers summarizing how many pending leave requests require attention.
    Designed for 9:00 AM M-F execution.
    """
    from core.models.leaves import LeaveRequest
    from core.models.organization import User
    from integrations.google.gmail import GmailService
    from django.utils import timezone
    
    managers = User.objects.filter(role__in=['manager', 'org_admin'], is_active=True)
    count = 0
    
    # We initialize the service once per run, defaulting to system integration (no user specified)
    try:
        gmail_service = GmailService()
    except Exception as e:
        logger.error(f"Failed to initialize Gmail API for digests: {e}")
        return {"status": "error", "error": str(e)}

    for manager in managers:
        pending_count = LeaveRequest.objects.filter(
            status='pending', 
            organization=manager.organization
        ).count()
        
        if pending_count > 0:
            subject = f"Action Required: {pending_count} Pending Requests"
            body = f"Hi {manager.name or manager.username},\n\nYou have {pending_count} pending leave requests waiting for your approval in Project Harvey.\n\nPlease log into the dashboard to review them."
            
            try:
                gmail_service.send_email(
                    recipient_email=manager.email,
                    subject=subject,
                    body=body
                )
                count += 1
            except Exception as e:
                logger.error(f"Failed to send digest to {manager.email}: {e}")
                
    return {"sent": count}

@shared_task(bind=True, max_retries=1)
def send_weekly_employee_summary(self):
    """
    Sends a weekly email to employees summarizing their accomplishments for the week.
    Designed for 4:00 PM Friday execution.
    """
    from core.models.leaves import LeaveRequest
    from core.models.organization import User
    from core.models.chatbot import GraphRun
    from core.models.recruitment import Interview
    from integrations.google.gmail import GmailService
    from django.utils import timezone
    import datetime
    
    users = User.objects.filter(is_active=True)
    count = 0
    
    try:
        gmail_service = GmailService()
    except Exception as e:
        logger.error(f"Failed to initialize Gmail API for weekly summaries: {e}")
        return {"status": "error", "error": str(e)}
        
    start_of_week = timezone.now().date() - datetime.timedelta(days=timezone.now().weekday())
    
    for user in users:
        # 1. Approved Leaves
        leaves_this_week = LeaveRequest.objects.filter(
            employee=user, 
            status='approved',
            start_date__gte=start_of_week
        ).count()
        
        # 2. AI Tasks completed
        ai_tasks = GraphRun.objects.filter(
            user=user,
            status='success',
            started_at__date__gte=start_of_week
        ).count()
        
        # 3. Interviews conducted
        interviews_count = Interview.objects.filter(
            interviewer=user,
            date_time__date__gte=start_of_week
        ).count()
        
        if leaves_this_week > 0 or ai_tasks > 0 or interviews_count > 0:
            from django.template.loader import render_to_string
            from django.utils.html import strip_tags
            
            end_of_week = start_of_week + datetime.timedelta(days=6)
            
            context = {
                'user_name': user.name or user.username,
                'start_date': start_of_week.strftime("%b %d"),
                'end_date': end_of_week.strftime("%b %d, %Y"),
                'ai_tasks': ai_tasks,
                'interviews_count': interviews_count,
                'leaves_this_week': leaves_this_week,
            }
            
            html_content = render_to_string('emails/weekly_summary.html', context)
            text_content = strip_tags(html_content)
            
            try:
                gmail_service.send_email(
                    recipient_email=user.email,
                    subject=f"Weekly Performance Insight: {start_of_week.strftime('%b %d')}",
                    body=text_content,
                    html_content=html_content
                )
                count += 1
            except Exception as e:
                logger.error(f"Failed to send weekly summary to {user.email}: {e}")
                
    return {"sent": count}
@shared_task(bind=True)
def cleanup_cancelled_interviews_task(self):
    """
    Weekly task to permanently remove cancelled interviews from the database.
    Designed for Sunday midnight execution.
    """
    from core.models.recruitment import Interview
    
    count, _ = Interview.objects.filter(status='cancelled').delete()
    
    logger.info("Database Cleanup: Removed %s cancelled interview records.", count)
    return {"deleted_count": count}
