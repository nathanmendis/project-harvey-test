import logging
import httpx
from typing import Optional, Dict, Any
from core.models.recruitment import HRMSSystemConfig
from .registry import HRMSAdapterRegistry

logger = logging.getLogger(__name__)

class HRMSIntegrationService:
    """Orchestrates syncing and data fetching from active HRMS endpoints"""
    
    def __init__(self, organization_id: int):
        self.organization_id = organization_id
        
        # Load the configuration from the database synchronously
        config = HRMSSystemConfig.objects.filter(
            organization_id=self.organization_id,
            is_active=True
        ).first()
        
        if not config:
            raise ValueError(f"No active HRMS integration configured for org {self.organization_id}")
        
        adapter_config = {
            'base_url': config.base_url,
            'auth_token': config.auth_token,
            'departments_endpoint': config.departments_endpoint,
            'employees_endpoint': config.employees_endpoint,
            'jobs_endpoint': config.jobs_endpoint,
            'candidates_endpoint': config.candidates_endpoint,
            'interviews_endpoint': config.interviews_endpoint,
            'onboarding_endpoint': config.onboarding_endpoint,
        }
        
        self._adapter = HRMSAdapterRegistry.get_adapter(
            config.hrms_type, 
            adapter_config
        )

    async def get_all_employees(self) -> list:
        adapter = self._adapter
        page = 1
        all_employees = []
        
        page_size = 500
        while True:
            response = await adapter.get_employees(page=page, page_size=page_size)
            employees = response if isinstance(response, list) else response.get('data', [])
            
            if not employees:
                break
                
            all_employees.extend(employees)
            if len(employees) < page_size:
                break
            page += 1
            
        return all_employees

    async def get_all_candidates(self) -> list:
        adapter = self._adapter
        page = 1
        all_candidates = []
        
        page_size = 500
        while True:
            response = await adapter.get_candidates(page=page, page_size=page_size)
            candidates = response if isinstance(response, list) else response.get('data', [])
            
            if not candidates:
                break
                
            all_candidates.extend(candidates)
            if len(candidates) < page_size:
                break
            page += 1
            
        return all_candidates

    async def get_all_interviews(self) -> list:
        adapter = self._adapter
        page = 1
        all_interviews = []
        
        page_size = 500
        while True:
            response = await adapter.get_interviews(page=page, page_size=page_size)
            interviews = response if isinstance(response, list) else response.get('data', [])
            
            if not interviews:
                break
                
            all_interviews.extend(interviews)
            if len(interviews) < page_size:
                break
            page += 1
            
        return all_interviews
