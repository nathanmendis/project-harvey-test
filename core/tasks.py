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
