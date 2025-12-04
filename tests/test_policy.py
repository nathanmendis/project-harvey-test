from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from core.models.policy import Policy, PolicyChunk
from core.models.organization import User, Organization
from core.services.policy_indexer import PolicyIndexer
from core.vector_store import get_vector_store
import os
import shutil

class PolicyFeatureTest(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="Test Org")
        self.user = User.objects.create_user(username="testuser", password="password", organization=self.org)
        self.indexer = PolicyIndexer()
        
        # Ensure clean vector store for tests (optional, but good practice)
        # In a real scenario, we'd mock the vector store or use a separate test index path.
        # For now, we assume the dev environment is okay to use or we just test the logic.

    def test_policy_upload_and_indexing(self):
        print("\nTesting Policy Upload and Indexing...")
        # Create a dummy text file
        content = b"This is a test policy content. Employees must wear hats on Fridays."
        uploaded_file = SimpleUploadedFile("policy.txt", content, content_type="text/plain")

        policy = Policy.objects.create(
            title="Hat Policy",
            source_type="upload",
            uploaded_file=uploaded_file,
            created_by=self.user
        )

        # Index
        print("Indexing policy...")
        success = self.indexer.index_policy(policy.id)
        self.assertTrue(success)
        
        policy.refresh_from_db()
        self.assertEqual(policy.status, "indexed")
        
        # Check chunks
        self.assertTrue(policy.chunks.exists())
        chunk = policy.chunks.first()
        self.assertIn("wear hats", chunk.text)
        print(f"Chunk created: {chunk.text}")

        # Check Vector Store Search
        print("Searching vector store...")
        vector_store = get_vector_store()
        # Allow some time for persistence if needed, but FAISS in memory should be instant
        results = vector_store.similarity_search("wear hats", k=1)
        
        found = False
        for res in results:
            if "wear hats" in res.page_content:
                found = True
                break
        
        self.assertTrue(found, "Should find the indexed text in vector store")
        print("Search successful.")
