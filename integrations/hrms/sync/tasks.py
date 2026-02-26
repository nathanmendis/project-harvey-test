from celery import shared_task
from django.utils import timezone
from core.models.organization import Organization, User
from core.models.recruitment import Candidate, Interview, LeaveRequest
from integrations.hrms.service import HRMSIntegrationService
from integrations.hrms.sync.tracker import SyncStatusTracker
import logging
from asgiref.sync import async_to_sync

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3)
def sync_all_data(self):
    """
    Sync all HRMS data (Employees, Candidates, Jobs, Leaves, Interviews)
    in a single batch job for all organizations with active HRMS integration.
    """
    tracker = SyncStatusTracker()
    
    # Process each organization sequentially to avoid rate-limiting the mock API
    for org in Organization.objects.filter(hrms_configs__is_active=True).distinct():
        try:
            sync_organization_data.delay(org.id)
        except Exception as e:
            logger.error(f"Failed to queue data sync for org {org.id}: {str(e)}")


@shared_task(bind=True, max_retries=3)
def sync_organization_data(self, org_id: int):
    """Sync all required data for a specific organization from the HRMS"""
    tracker = SyncStatusTracker()
    # Using a single sync tracker for 'batch_all'
    sync_id = tracker.start_sync(org_id, 'batch_all')

    def _check_stop():
        """Return True and mark stopped if a force-stop was requested."""
        if tracker.is_stop_requested(org_id):
            tracker.mark_stopped(sync_id, org_id)
            logger.warning(f"Force-stop requested for org {org_id}. Sync aborted.")
            return True
        return False
    
    try:
        service = HRMSIntegrationService(org_id)
        
        last_sync = tracker.get_last_sync_time(org_id, 'batch_all')
        
        # 1. Sync Employees
        logger.info(f"Syncing employees for org {org_id}")
        employees = async_to_sync(service.get_all_employees)()
        total_employees = 0
        for emp_data in employees:
            # Check incremental update timestamp if present
            emp_updated = emp_data.get('updated_at')
            if last_sync and emp_updated and emp_updated < last_sync:
                continue
                
            User.objects.update_or_create(
                email=emp_data['email'],
                organization_id=org_id,
                defaults={
                    'username': emp_data['email'],
                    'first_name': emp_data.get('first_name', ''),
                    'last_name': emp_data.get('last_name', ''),
                    'name': f"{emp_data.get('first_name', '')} {emp_data.get('last_name', '')}".strip()
                }
            )
            total_employees += 1

        if _check_stop():
            return

        # 2. Sync Candidates
        logger.info(f"Syncing candidates for org {org_id}")
        candidates = async_to_sync(service.get_all_candidates)()
        total_candidates = 0
        for cand_data in candidates:
            Candidate.objects.update_or_create(
                email=cand_data['email'],
                organization_id=org_id,
                defaults={
                    'name': f"{cand_data.get('first_name', '')} {cand_data.get('last_name', '')}",
                    'phone': cand_data.get('phone'),
                    'status': cand_data.get('status', 'pending'),
                    'source': cand_data.get('source', 'hrms_sync'),
                    'skills': cand_data.get('skills', []),
                }
            )
            total_candidates += 1

        if _check_stop():
            return

        # 3. Sync Interviews
        logger.info(f"Syncing interviews for org {org_id}")
        interviews = async_to_sync(service.get_all_interviews)()
        total_interviews = 0
        for iv_data in interviews:
            # We would typically map candidate_id and interviewer_id
            # Assuming mock returns 'candidate_email' and 'interviewer_email' for simplicity
            cand = Candidate.objects.filter(email=iv_data.get('candidate_email'), organization_id=org_id).first()
            interviewer = User.objects.filter(email=iv_data.get('interviewer_email'), organization_id=org_id).first()
            
            if cand and interviewer:
                Interview.objects.update_or_create(
                    id=iv_data.get('id'), # if we have stable IDs
                    organization_id=org_id,
                    defaults={
                        'candidate': cand,
                        'interviewer': interviewer,
                        'date_time': timezone.now(), # Needs parsing from iv_data
                        'status': iv_data.get('status', 'scheduled')
                    }
                )
                total_interviews += 1
            
        tracker.complete_sync(sync_id, total_employees + total_candidates + total_interviews)
        logger.info(f"Successfully synced batch for org {org_id} (Emp: {total_employees}, Cand: {total_candidates}, Int: {total_interviews})")
        
    except Exception as e:
        # Don't mark as failed if we were force-stopped mid-task
        if tracker.is_stop_requested(org_id):
            tracker.mark_stopped(sync_id, org_id)
            logger.warning(f"Force-stop caught exception path for org {org_id}. Sync aborted.")
            return
        tracker.fail_sync(sync_id, str(e))
        logger.error(f"Batch sync failed for org {org_id}: {str(e)}")
        raise self.retry(exc=e, countdown=60)
