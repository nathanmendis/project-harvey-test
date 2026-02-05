from django.test import TransactionTestCase
from unittest.mock import patch, MagicMock
from django.core.files.uploadedfile import SimpleUploadedFile
from core.models.recruitment import Candidate, JobRole
from core.models.organization import Organization, User

class TestKnowledgeBaseIndexing(TransactionTestCase):
    
    def setUp(self):
        self.org = Organization.objects.create(name="Test Org")
        self.user = User.objects.create(username="testadmin", organization=self.org)

    @patch('core.ai.rag.model_indexer.get_vector_store')
    def test_candidate_indexing_signal(self, mock_get_store):
        # Setup mock
        mock_store_instance = MagicMock()
        mock_get_store.return_value = mock_store_instance
        
        # Create candidate
        resume = SimpleUploadedFile("resume.txt", b"Skills: Python, Django")
        candidate = Candidate.objects.create(
            organization=self.org,
            name="Alice Indexer",
            email="alice@example.com",
            skills=["Python", "AI"],
            resume_file=resume
        )

        # Allow thread to run (signals use threads)
        import time
        time.sleep(1) # Give thread a moment

        # Verify add_documents was called
        self.assertTrue(mock_store_instance.add_documents.called)
        
        # Verify content
        args, _ = mock_store_instance.add_documents.call_args
        text_content = args[0][0]
        self.assertIn("Alice Indexer", text_content)
        self.assertIn("Python, AI", text_content)

    @patch('core.ai.rag.model_indexer.get_vector_store')
    def test_job_role_indexing_signal(self, mock_get_store):
         # Setup mock
        mock_store_instance = MagicMock()
        mock_get_store.return_value = mock_store_instance

        # Create Job Role
        job = JobRole.objects.create(
            organization=self.org,
            title="Senior AI Engineer",
            department="Engineering",
            description="Build cool agents",
            requirements="Python 3.12"
        )

        # Allow thread to run
        import time
        time.sleep(1) 

        # Verify
        self.assertTrue(mock_store_instance.add_documents.called)
        args, _ = mock_store_instance.add_documents.call_args
        text_content = args[0][0]
        self.assertIn("Senior AI Engineer", text_content)
        self.assertIn("Build cool agents", text_content)
