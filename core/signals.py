import os
from django.db.models.signals import post_delete
from django.dispatch import receiver
from core.models.policy import Policy


@receiver(post_delete, sender=Policy)
def delete_policy_file(sender, instance, **kwargs):
    """
    Deletes the uploaded file from the filesystem when a Policy is deleted.
    Candidate / JobRole indexing is handled by the Celery periodic task
    (core.tasks.index_candidates_and_jobs) which runs every 2 hours.
    """
    if instance.uploaded_file:
        if os.path.isfile(instance.uploaded_file.path):
            try:
                os.remove(instance.uploaded_file.path)
                print(f"Deleted file: {instance.uploaded_file.path}")
            except Exception as e:
                print(f"Error deleting file: {e}")

import logging
from django.db.models.signals import post_save
from core.models.leaves import LeaveRequest, LeaveBalance, OrganizationLeavePolicy
from core.models.recruitment import Candidate

@receiver(post_save, sender=OrganizationLeavePolicy)
def trigger_leave_balance_allocation(sender, instance, created, **kwargs):
    """
    When an OrganizationLeavePolicy is added or updated, queue a celery task 
    to asynchronously cascade the balance to all employees so the server doesn't block.
    """
    from core.tasks import allocate_leave_balances_task
    from django.db import transaction
    
    transaction.on_commit(lambda: allocate_leave_balances_task.delay(instance.id))

@receiver(post_save, sender=LeaveRequest)
def deduct_leave_balance_on_approval(sender, instance, created, **kwargs):
    """
    When a LeaveRequest is marked 'approved', deduct the corresponding
    days from the employee's LeaveBalance for that specific year.
    """
    if instance.status == 'approved' and not instance.is_deducted:
        days = (instance.end_date - instance.start_date).days + 1
        year = instance.start_date.year

        balance, _ = LeaveBalance.objects.get_or_create(
            employee=instance.employee,
            organization=instance.organization,
            year=year,
            leave_type=instance.leave_type,
            defaults={'total_allocated': 0.0, 'used': 0.0}
        )

        balance.used += days
        balance.save()

        instance.is_deducted = True
        # Use update() to avoid triggering post_save again
        LeaveRequest.objects.filter(pk=instance.pk).update(is_deducted=True)


@receiver(post_save, sender=Candidate)
def trigger_candidate_resume_parsing(sender, instance, created, **kwargs):
    """
    When a Candidate is created or updated, if they have a resume_file but no skills
    or parsed_data set yet, trigger the async parsing task.
    """
    if instance.resume_file and (not instance.skills or not instance.parsed_data):
        from core.tasks import parse_candidate_resume_task
        from django.db import transaction
        transaction.on_commit(lambda: parse_candidate_resume_task.delay(instance.id))

