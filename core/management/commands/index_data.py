from django.core.management.base import BaseCommand
from core.models.recruitment import Candidate, JobRole
from core.vector_store import get_vector_store

class Command(BaseCommand):
    help = 'Indexes Candidate and JobRole data into FAISS vector store'

    def handle(self, *args, **kwargs):
        self.stdout.write("Starting indexing process...")
        
        store = get_vector_store()
        texts = []
        metadatas = []

        # Index Candidates
        candidates = Candidate.objects.all()
        for c in candidates:
            # Create a rich text representation
            text = f"Candidate: {c.name}\nEmail: {c.email}\nPhone: {c.phone}\nSkills: {c.skills}"
            texts.append(text)
            metadatas.append({"type": "candidate", "id": c.id, "name": c.name})
        
        self.stdout.write(f"Found {len(candidates)} candidates.")

        # Index Job Roles
        roles = JobRole.objects.all()
        for r in roles:
            text = f"Job Role: {r.title}\nDepartment: {r.department}\nDescription: {r.description}\nRequirements: {r.requirements}"
            texts.append(text)
            metadatas.append({"type": "job_role", "id": r.id, "title": r.title})

        self.stdout.write(f"Found {len(roles)} job roles.")

        if texts:
            self.stdout.write("Creating embeddings and indexing...")
            store.create_index(texts, metadatas)
            self.stdout.write(self.style.SUCCESS("Successfully indexed data."))
        else:
            self.stdout.write(self.style.WARNING("No data found to index."))
