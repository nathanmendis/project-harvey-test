import uuid
from datetime import datetime
from django.utils import timezone
import redis
import json
from django.conf import settings

# Setting up a separate Redis connection for Celery/HRMS sync tracking
# We use db=1 to avoid overwriting LLM cache keys on db=0
REDIS_URL = getattr(settings, 'CELERY_BROKER_URL', 'redis://localhost:6379/1')

class SyncStatusTracker:
    """Track sync status and incremental history in a separate Redis DB"""
    
    def __init__(self):
        self.client = redis.from_url(REDIS_URL, decode_responses=True)
        
    def _set_cache(self, key: str, value: dict, timeout: int = None):
        self.client.set(key, json.dumps(value))
        if timeout:
            self.client.expire(key, timeout)
            
    def _get_cache(self, key: str) -> dict:
        data = self.client.get(key)
        return json.loads(data) if data else None

    def start_sync(self, org_id: int, entity_type: str) -> str:
        """Start a new sync operation"""
        sync_id = str(uuid.uuid4())
        
        sync_data = {
            'sync_id': sync_id,
            'org_id': org_id,
            'entity_type': entity_type,
            'status': 'running',
            'started_at': timezone.now().isoformat(),
            'records_synced': 0,
        }
        
        # Store sync data for 1 hour
        self._set_cache(f"hrms_sync:{sync_id}", sync_data, timeout=3600)
        # Store latest sync ID for a day
        self._set_cache(f"hrms_sync_latest:{org_id}:{entity_type}", sync_id, timeout=86400)
        # Clear any previous stop request when a new sync starts
        self.client.delete(f"hrms_sync_stop:{org_id}")
        
        return sync_id
    
    def complete_sync(self, sync_id: str, records_synced: int):
        """Mark sync as completed successfully"""
        sync_data = self._get_cache(f"hrms_sync:{sync_id}")
        if sync_data:
            sync_data.update({
                'status': 'completed',
                'completed_at': timezone.now().isoformat(),
                'records_synced': records_synced,
            })
            self._set_cache(f"hrms_sync:{sync_id}", sync_data, timeout=86400)
            
            # Update last successful sync time (never expires)
            org_id = sync_data['org_id']
            entity_type = sync_data['entity_type']
            
            # Save the raw ISO string directly
            self.client.set(
                f"hrms_last_sync:{org_id}:{entity_type}",
                timezone.now().isoformat()
            )
    
    def fail_sync(self, sync_id: str, error: str):
        """Mark sync as failed"""
        sync_data = self._get_cache(f"hrms_sync:{sync_id}")
        if sync_data:
            sync_data.update({
                'status': 'failed',
                'failed_at': timezone.now().isoformat(),
                'error': error,
            })
            self._set_cache(f"hrms_sync:{sync_id}", sync_data, timeout=86400)
    
    def get_last_sync_time(self, org_id: int, entity_type: str) -> datetime:
        """Get timestamp of last successful sync for incremental pulling"""
        last_sync_str = self.client.get(f"hrms_last_sync:{org_id}:{entity_type}")
        if last_sync_str:
            return datetime.fromisoformat(last_sync_str)
        return None
    
    def get_sync_status(self, sync_id: str) -> dict:
        """Get status of a specific sync operation"""
        return self._get_cache(f"hrms_sync:{sync_id}")
        
    def get_latest_sync_status(self, org_id: int, entity_type: str) -> dict:
        """Get status of the most recent sync operation"""
        sync_id = self._get_cache(f"hrms_sync_latest:{org_id}:{entity_type}")
        if sync_id:
            return self.get_sync_status(sync_id)
        return None

    def get_latest_running_sync_id(self, org_id: int, entity_type: str) -> str:
        """Return the sync_id if the latest sync is still running, else None"""
        raw = self.client.get(f"hrms_sync_latest:{org_id}:{entity_type}")
        if not raw:
            return None
        sync_id = raw  # stored as a plain string, not JSON
        status_data = self.get_sync_status(sync_id)
        if status_data and status_data.get('status') == 'running':
            return sync_id
        return None

    # ------------------------------------------------------------------ #
    # Force-stop helpers                                                   #
    # ------------------------------------------------------------------ #

    def request_stop(self, org_id: int):
        """Signal the running sync to abort at its next checkpoint."""
        self.client.setex(f"hrms_sync_stop:{org_id}", 3600, "1")

    def is_stop_requested(self, org_id: int) -> bool:
        """Check whether a stop has been requested for this org's sync."""
        return self.client.exists(f"hrms_sync_stop:{org_id}") == 1

    def clear_stop_request(self, org_id: int):
        """Remove the stop flag after the sync has been aborted."""
        self.client.delete(f"hrms_sync_stop:{org_id}")

    def mark_stopped(self, sync_id: str, org_id: int):
        """Mark a sync as force-stopped and clean up the stop flag."""
        sync_data = self._get_cache(f"hrms_sync:{sync_id}")
        if sync_data:
            sync_data.update({
                'status': 'stopped',
                'stopped_at': timezone.now().isoformat(),
            })
            self._set_cache(f"hrms_sync:{sync_id}", sync_data, timeout=86400)
        self.clear_stop_request(org_id)
