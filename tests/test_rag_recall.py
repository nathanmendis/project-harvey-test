import json
from django.test import TransactionTestCase
from django.contrib.auth import get_user_model
from core.models.policy import Policy
from core.ai.rag.tools.policy_search_tool import search_policies

User = get_user_model()

class RAGRecallTests(TransactionTestCase):
    def setUp(self):
        from core.models.organization import Organization
        from core.ai.rag.policy_indexer import PolicyIndexer
        from core.ai.rag.vector_store import get_vector_store
        
        # 1. Setup Data
        self.org = Organization.objects.create(name="Harvey Test Org")
        self.user = User.objects.create_user(
            username="test_rag_user",
            password="password",
            organization=self.org
        )
        
        self.policy = Policy.objects.create(
            title="Mini HR Policy",
            description="Test policy",
            source_type="upload",
            created_by=self.user,
            status="pending"
        )
        
        # 2. Add Mini-Policy Content
        # We simulate the extraction text directly to test the indexer logic
        mini_policy_text = """
        1. Working Hours
        Standard working hours are 9 hours per day.
        2. Performance
        Employees undergo periodic performance evaluations.
        3. Leave
        Casual Leave is available. (Value not specified)
        """
        
        # 3. Index the mini policy
        # We manually drive the indexer to use our text
        indexer = PolicyIndexer()
        # Clean old test data if any
        get_vector_store().delete_all()
        
        chunks = indexer.text_splitter.split_text(mini_policy_text)
        texts = []
        metadatas = []
        for i, chunk in enumerate(chunks):
             texts.append(chunk)
             metadatas.append({
                 "source": self.policy.title,
                 "title": self.policy.title,
                 "policy_id": str(self.policy.id),
                 "chunk_index": i,
                 "type": "policy",
                 "doc_type": "policy",
                 "organization_id": str(self.org.id)
             })
        indexer.vector_store.add_documents(texts, metadatas)

    def test_working_hours_recall(self):
        """Verify that working hours query retrieves the 9-hour rule."""
        query = "How many working hours are employees expected to work per day?"
        result_json = search_policies.func(query, user=self.user)
        result = json.loads(result_json)
        
        message = result.get("message", "").lower()
        self.assertIn("9 hours", message)
        self.assertTrue(result.get("ok"))

    def test_performance_management_recall(self):
        """Verify that performance queries retrieve periodic evaluation info."""
        query = "How often are performance evaluations conducted?"
        result_json = search_policies.func(query, user=self.user)
        result = json.loads(result_json)
        
        message = result.get("message", "").lower()
        self.assertIn("periodic", message)

    def test_gate_blocks_unanswerable_quantitative(self):
        """Verify the Answerability Gate blocks queries with missing numbers."""
        query = "How many casual leaves are employees entitled to?"
        result_json = search_policies.func(query, user=self.user)
        result = json.loads(result_json)
        
        message = result.get("message", "")
        # The mini-policy text has no numbers for leave, so it should be blocked
        self.assertIn("not specify", message)

    def test_intent_dominance(self):
        """Verify that intent-heavy chunks (Leave) dominate mismatching chunks."""
        query = "What types of leave are available?"
        result_json = search_policies.func(query, user=self.user)
        result = json.loads(result_json)
        
        message = result.get("message", "").lower()
        # Should mention CL/SL/EL etc from the Leave section, not recruitment
        self.assertIn("casual", message)
        self.assertIn("sick", message)
