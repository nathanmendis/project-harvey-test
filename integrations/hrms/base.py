from typing import Dict, Optional, Any
from abc import ABC, abstractmethod


class HRMSAdapter(ABC):
    """
    Base interface for all HRMS integrations.
    Any new HRMS systems (Workday, BambooHR, Harvey Mock) must implement this interface
    to ensure scalable and plug-and-play integration.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.base_url = config.get('base_url')
        self.auth_token = config.get('auth_token')
    
    @abstractmethod
    async def get_departments(self, page: int = 1, page_size: int = 50) -> Dict[str, Any]:
        """Fetch departments from HRMS"""
        pass

    @abstractmethod
    async def get_employees(self, page: int = 1, page_size: int = 50) -> Dict[str, Any]:
        """Fetch employees from HRMS"""
        pass
    
    @abstractmethod
    async def get_employee(self, employee_id: str) -> Dict[str, Any]:
        """Fetch single employee details"""
        pass
    
    @abstractmethod
    async def get_job_requisitions(self, status: str = 'open', page: int = 1, page_size: int = 50) -> Dict[str, Any]:
        """Fetch job openings"""
        pass
    
    @abstractmethod
    async def get_candidates(self, job_id: Optional[str] = None, page: int = 1, page_size: int = 50) -> Dict[str, Any]:
        """Fetch candidates"""
        pass
    
    @abstractmethod
    async def create_candidate(self, candidate_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create new candidate in HRMS"""
        pass
    
    @abstractmethod
    async def get_interviews(self, page: int = 1, page_size: int = 50) -> Dict[str, Any]:
        """Fetch interviews"""
        pass

    @abstractmethod
    async def schedule_interview(self, interview_data: Dict[str, Any]) -> Dict[str, Any]:
        """Schedule interview in HRMS"""
        pass
    
    @abstractmethod
    async def get_leave_requests(self, employee_id: Optional[str] = None, page: int = 1, page_size: int = 50) -> Dict[str, Any]:
        """Fetch leave requests"""
        pass
    
    @abstractmethod
    async def create_leave_request(self, leave_data: Dict[str, Any]) -> Dict[str, Any]:
        """Submit leave request"""
        pass
