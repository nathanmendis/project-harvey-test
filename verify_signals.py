
import os
import django
import time
import sys
from unittest.mock import MagicMock, patch

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project_harvey.settings")
django.setup()

from core.models.recruitment import Candidate, JobRole
from core.models.organization import Organization, User

def run_verification():
    print("🚀 Starting verification...")
    
    # Mock the vector store in the services module
    # We need to patch where it is IMPORTED or USED
    with patch('core.services.model_indexer.get_vector_store') as mock_get_store:
        mock_store = MagicMock()
        mock_get_store.return_value = mock_store
        
        # Create Org
        org, _ = Organization.objects.get_or_create(name="Signal Test Org")
        
        print("Creating Candidate...")
        # Create Candidate
        Candidate.objects.create(
            organization=org,
            name="Signal Test Candidate",
            email="signal@test.com",
            skills=["Signal", "Processing"],
            resume_file="dummy.txt"
        )
        
        print("Waiting for thread...")
        time.sleep(2)
        
        if mock_store.add_documents.called:
            print("✅ Candidate indexing Triggered!")
        else:
            print("❌ Candidate indexing NOT Triggered.")

        # Reset mock
        mock_store.reset_mock()

        print("Creating Job Role...")
        JobRole.objects.create(
            organization=org,
            title="Signal Test Job",
            department="QA",
            description="Test signals",
            requirements="None"
        )

        print("Waiting for thread...")
        time.sleep(2)

        if mock_store.add_documents.called:
            print("✅ Job Role indexing Triggered!")
        else:
            print("❌ Job Role indexing NOT Triggered.")

if __name__ == "__main__":
    try:
        run_verification()
    except Exception as e:
        print(f"❌ Error: {e}")
