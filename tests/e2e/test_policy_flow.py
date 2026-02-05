from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from core.models.organization import Organization, User
from core.models.policy import Policy
from core.ai.rag.policy_indexer import PolicyIndexer
from core.vector_store import get_vector_store
from core.ai.rag.tools.policy_search_tool import search_policies
import json

class PolicyFlowTest(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="Tech Corp")
        self.user = User.objects.create_user(username="policy_mgr", password="password", organization=self.org)
        self.indexer = PolicyIndexer()

    def test_rag_pipeline(self):
        print("\n--- Starting Policy RAG E2E ---")

        # 1. Upload Policy
        print("1. Uploading Policy...")
        content = b"All employees are entitled to 25 days of paid annual leave per year."
        uploaded_file = SimpleUploadedFile("leave_policy.txt", content, content_type="text/plain")
        
        policy = Policy.objects.create(
            title="Annual Leave Policy",
            source_type="upload",
            uploaded_file=uploaded_file,
            created_by=self.user
        )
        self.assertEqual(policy.status, "pending")

        # 2. Index Policy
        print("2. Indexing...")
        success = self.indexer.index_policy(policy.id)
        self.assertTrue(success)
        policy.refresh_from_db()
        self.assertEqual(policy.status, "indexed")
        
        # Verify chunks
        self.assertTrue(policy.chunks.exists())
        print(f"Chunks created: {policy.chunks.count()}")

        # 3. Vector Search (Direct)
        print("3. Verifying Vector Store...")
        vs = get_vector_store()
        # Filter by Org
        filter_args = {"filter": {"organization_id": str(self.org.id)}}
        results = vs.similarity_search("annual leave", k=1, **filter_args)
        
        self.assertTrue(len(results) > 0)
        self.assertIn("25 days", results[0].page_content)
        self.assertEqual(results[0].metadata.get("organization_id"), str(self.org.id))

        # 4. Tool Execution (Search Tool)
        print("4. Testing Search Tool...")
        # The tool expects user context for filtering
        res_json = search_policies.func(query="How many paid leave days?", user=self.user)
        res = json.loads(res_json)
        
        self.assertTrue(res.get("ok"))
        self.assertIn("25 days", res.get("message"))
        print(f"Tool Result: {res.get('message')}")

        print("--- Policy RAG Flow Passed ---")
    
    def tearDown(self):
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT pg_terminate_backend(pid) 
                FROM pg_stat_activity 
                WHERE datname = current_database() 
                AND pid <> pg_backend_pid();
            """)
