from django.core.management.base import BaseCommand
from core.models.policy import Policy
from core.models.recruitment import Candidate, JobRole
from core.services.policy_indexer import PolicyIndexer
from core.services.model_indexer import ModelIndexer

class Command(BaseCommand):
    help = 'Re-indexes all Candidates, Job Roles, and Policies with updated metadata'

    def handle(self, *args, **options):
        self.stdout.write("Starting re-indexing process...")
        
        policy_indexer = PolicyIndexer()
        model_indexer = ModelIndexer()

        # Re-index Policies
        policies = Policy.objects.all()
        self.stdout.write(f"Re-indexing {policies.count()} policies...")
        for policy in policies:
            success = policy_indexer.index_policy(policy.id)
            if success:
                self.stdout.write(self.style.SUCCESS(f"Indexed Policy: {policy.title}"))
            else:
                self.stdout.write(self.style.ERROR(f"Failed to index Policy: {policy.title}"))

        # Re-index Candidates
        candidates = Candidate.objects.all()
        self.stdout.write(f"Re-indexing {candidates.count()} candidates...")
        for candidate in candidates:
            success = model_indexer.index_candidate(candidate.id)
            if success:
                self.stdout.write(self.style.SUCCESS(f"Indexed Candidate: {candidate.name}"))
            else:
                self.stdout.write(self.style.ERROR(f"Failed to index Candidate: {candidate.name}"))

        # Re-index Job Roles
        job_roles = JobRole.objects.all()
        self.stdout.write(f"Re-indexing {job_roles.count()} job roles...")
        for job in job_roles:
            success = model_indexer.index_job_role(job.id)
            if success:
                self.stdout.write(self.style.SUCCESS(f"Indexed Job Role: {job.title}"))
            else:
                self.stdout.write(self.style.ERROR(f"Failed to index Job Role: {job.title}"))

        self.stdout.write(self.style.SUCCESS("Re-indexing complete!"))
