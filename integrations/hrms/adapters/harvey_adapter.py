import httpx
from typing import Dict, Optional, Any
from ..base import HRMSAdapter


class HarveyHRMSAdapter(HRMSAdapter):
    """
    Harvey HRMS Adapter connecting to the testing mock API server.
    Implements Pattern B scalability interface.
    """
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        # the auth token expects an X-API-Token for the harvey mock server
        self.headers = {"X-API-Token": self.auth_token}

    async def get_departments(self, page: int = 1, page_size: int = 50) -> Dict[str, Any]:
        endpoint = self.config.get("departments_endpoint", "/api/v1/departments")
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}{endpoint}",
                params={"page": page, "page_size": page_size},
                headers=self.headers,
                timeout=10.0
            )
            response.raise_for_status()
            return response.json()

    async def get_employees(self, page: int = 1, page_size: int = 50) -> Dict[str, Any]:
        endpoint = self.config.get("employees_endpoint", "/api/v1/employees")
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}{endpoint}",
                params={"page": page, "page_size": page_size},
                headers=self.headers,
                timeout=10.0
            )
            response.raise_for_status()
            return response.json()

    async def get_employee(self, employee_id: str) -> Dict[str, Any]:
        endpoint = self.config.get("employees_endpoint", "/api/v1/employees")
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}{endpoint}/{employee_id}",
                headers=self.headers,
                timeout=10.0
            )
            response.raise_for_status()
            return response.json()

    async def get_job_requisitions(self, status: str = 'open', page: int = 1, page_size: int = 50) -> Dict[str, Any]:
        endpoint = self.config.get("jobs_endpoint", "/api/v1/jobs")
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}{endpoint}",
                params={"status": status, "page": page, "page_size": page_size},
                headers=self.headers,
                timeout=10.0
            )
            response.raise_for_status()
            return response.json()

    async def get_candidates(self, job_id: Optional[str] = None, page: int = 1, page_size: int = 50) -> Dict[str, Any]:
        endpoint = self.config.get("candidates_endpoint", "/api/v1/candidates")
        async with httpx.AsyncClient() as client:
            params = {"page": page, "page_size": page_size}
            if job_id:
                params["job_id"] = job_id
            response = await client.get(
                f"{self.base_url}{endpoint}",
                params=params,
                headers=self.headers,
                timeout=10.0
            )
            response.raise_for_status()
            return response.json()

    async def create_candidate(self, candidate_data: Dict[str, Any]) -> Dict[str, Any]:
        endpoint = self.config.get("candidates_endpoint", "/api/v1/candidates")
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}{endpoint}",
                json=candidate_data,
                headers=self.headers,
                timeout=10.0
            )
            response.raise_for_status()
            return response.json()
            
    async def get_interviews(self, page: int = 1, page_size: int = 50) -> Dict[str, Any]:
        endpoint = self.config.get("interviews_endpoint", "/api/v1/interviews")
        async with httpx.AsyncClient() as client:
            params = {"page": page, "page_size": page_size}
            response = await client.get(
                f"{self.base_url}{endpoint}",
                params=params,
                headers=self.headers,
                timeout=10.0
            )
            response.raise_for_status()
            return response.json()

    async def schedule_interview(self, interview_data: Dict[str, Any]) -> Dict[str, Any]:
        endpoint = self.config.get("interviews_endpoint", "/api/v1/interviews")
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}{endpoint}",
                json=interview_data,
                headers=self.headers,
                timeout=10.0
            )
            response.raise_for_status()
            return response.json()

    async def get_leave_requests(self, employee_id: Optional[str] = None, page: int = 1, page_size: int = 50) -> Dict[str, Any]:
        endpoint = self.config.get("onboarding_endpoint", "/api/v1/onboarding")
        async with httpx.AsyncClient() as client:
            params = {"page": page, "page_size": page_size}
            if employee_id:
                params["employee_id"] = employee_id
            response = await client.get(
                f"{self.base_url}{endpoint}",
                params=params,
                headers=self.headers,
                timeout=10.0
            )
            response.raise_for_status()
            return response.json()

    async def create_leave_request(self, leave_data: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError("Leave requests creation not supported on mock server")
