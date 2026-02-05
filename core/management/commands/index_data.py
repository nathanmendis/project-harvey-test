from django.core.management.base import BaseCommand
from core.models.recruitment import Candidate, JobRole
from core.models.policy import Policy
from core.services.model_indexer import ModelIndexer
from core.services.policy_indexer import PolicyIndexer
from core.vector_store import get_vector_store

class Command(BaseCommand):
    help = 'Indexes Candidate, JobRole, and Policy data into PostgreSQL vector store using strict metadata'

    def handle(self, *args, **kwargs):
        self.stdout.write("Starting strict indexing process...")
        
        # Clear existing index to ensure "perfect" state
        store = get_vector_store()
        try:
            store.delete_all()
            self.stdout.write(self.style.SUCCESS("Cleared existing vector index."))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"Could not clear index: {e}"))

        model_indexer = ModelIndexer()
        policy_indexer = PolicyIndexer()

        # Index Candidates
        candidates = Candidate.objects.all()
        for c in candidates:
            model_indexer.index_candidate(c.id)
        self.stdout.write(f"✅ Indexed {len(candidates)} candidates.")

        # Index Job Roles
        roles = JobRole.objects.all()
        for r in roles:
            model_indexer.index_job_role(r.id)
        self.stdout.write(f"✅ Indexed {len(roles)} job roles.")

        # Index Policies
        policies = Policy.objects.all()
        for p in policies:
            policy_indexer.index_policy(p.id)
        self.stdout.write(f"✅ Indexed {len(policies)} policies.")

        self.stdout.write(self.style.SUCCESS("Successfully re-indexed all data with strict metadata."))
