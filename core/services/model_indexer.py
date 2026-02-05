import json
from core.models.recruitment import Candidate, JobRole
from core.vector_store import get_vector_store

class ModelIndexer:
    def __init__(self):
        self.vector_store = get_vector_store()

    def index_candidate(self, candidate_id):
        try:
            candidate = Candidate.objects.get(id=candidate_id)
            
            # Construct a rich text representation
            skills_str = ", ".join(candidate.skills) if candidate.skills else "None"
            resume_data = ""
            if candidate.parsed_data:
                 # Extract summary or key details if available
                 if isinstance(candidate.parsed_data, dict):
                     resume_data = json.dumps(candidate.parsed_data)
                 else:
                     resume_data = str(candidate.parsed_data)

            text_content = (
                f"Candidate Name: {candidate.name}\n"
                f"Email: {candidate.email}\n"
                f"Skills: {skills_str}\n"
                f"Resume Data: {resume_data}\n"
                f"Organization: {candidate.organization.name}"
            )

            metadata = {
                "source": candidate.name,
                "name": candidate.name,
                "email": candidate.email,
                "skills": skills_str,
                "type": "candidate",
                "doc_type": "candidate",
                "candidate_id": str(candidate.id),
                "organization_id": str(candidate.organization.id)
            }

            # Add to vector store (we add a SINGLE document for the candidate for now)
            # In a real system we might split resume text if it's huge
            self.vector_store.add_documents([text_content.strip()], [metadata])
            print(f"✅ Indexed Candidate: {candidate.name}")
            return True

        except Exception as e:
            print(f"❌ Error indexing candidate {candidate_id}: {e}")
            return False

    def index_job_role(self, job_id):
        try:
            job = JobRole.objects.get(id=job_id)

            text_content = (
                f"Job Title: {job.title}\n"
                f"Department: {job.department}\n"
                f"Description: {job.description}\n"
                f"Requirements: {job.requirements}\n"
                f"Organization: {job.organization.name}"
            )

            metadata = {
                "source": job.title,
                "title": job.title,
                "department": job.department,
                "type": "job_role",
                "doc_type": "job",
                "job_id": str(job.id),
                "organization_id": str(job.organization.id)
            }

            self.vector_store.add_documents([text_content.strip()], [metadata])
            print(f"✅ Indexed Job Role: {job.title}")
            return True
        except Exception as e:
            print(f"❌ Error indexing job {job_id}: {e}")
            return False
