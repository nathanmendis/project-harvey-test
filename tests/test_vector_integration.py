from django.test import TestCase
from core.models.recruitment import Candidate, JobRole
from core.models.organization import Organization
from core.vector_store import get_vector_store
from django.core.management import call_command
import time

class VectorStoreIntegrationTest(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="Tech Corp")
        
        self.candidate = Candidate.objects.create(
            organization=self.org,
            name="Alice Python",
            email="alice@example.com",
            phone="1234567890",
            skills=["Python", "Django", "PostgreSQL", "Docker"],
            source="LinkedIn"
        )
        
        self.job_role = JobRole.objects.create(
            organization=self.org,
            title="Senior Backend Engineer",
            department="Engineering",
            description="Build scalable APIs",
            requirements="Expert in Python, Django, and Vector DBs"
        )

    def test_indexing_and_search(self):
        # Run indexing command
        call_command('index_data')
        
        # Verify search
        store = get_vector_store()
        query = "python developer"
        results = store.similarity_search(query, k=2)
        
        self.assertTrue(len(results) > 0, "Should find at least one result")
        
        # Check if we found our candidate or job role
        found_candidate = False
        found_job = False
        
        for res in results:
            if res.metadata.get('type') == 'candidate' and res.metadata.get('name') == 'Alice Python':
                found_candidate = True
            if res.metadata.get('type') == 'job_role' and res.metadata.get('title') == 'Senior Backend Engineer':
                found_job = True
                
        self.assertTrue(found_candidate or found_job, "Should find relevant candidate or job role")
