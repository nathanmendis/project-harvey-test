from django.utils import timezone
from django.db.models import Q
from langchain_core.tools import tool
from core.models.recruitment import Candidate, CandidateJobScore, JobRole
from core.ai.utils.resume_parser import ResumeParser
from core.ai.utils.candidate_scorer import CandidateScorer
from core.ai.agentic.tools.utils import ok, err, get_org
import os

@tool("add_candidate", return_direct=True)
def add_candidate(name: str, email: str, skills: str, phone: str, source: str = "Chatbot", user=None) -> str:
    """Adds a new candidate to your organization's HR system."""
    org = get_org(user)
    if not org:
        return err("User is not associated with any organization. Please contact support.")

    if Candidate.objects.filter(email=email, organization=org).exists():
        return err(f"A candidate with the email '{email}' is already in the system.")

    c = Candidate.objects.create(
        organization=org,
        name=name,
        email=email,
        phone=phone,
        skills=[s.strip() for s in skills.split(",")] if skills else [],
        source=source,
        status="pending",
    )
    return ok(f"I've successfully added {name} as a new candidate.", id=c.id, name=name)


@tool("add_candidate_with_resume", return_direct=True)
def add_candidate_with_resume(file_path: str, name: str = "", email: str = "", phone: str = "", user=None) -> str:
    """
    Adds a candidate by parsing their resume (PDF/DOCX).
    If name/email are not provided, tries to extract them (simplified).
    """
    org = get_org(user)
    if not org:
        return err("User is not associated with any organization. Please contact support.")

    # Fix: Resolve file path if it's just a filename
    if not os.path.exists(file_path):
        # Try finding it in 'resumes' folder
        potential_path = os.path.join("resumes", os.path.basename(file_path))
        if os.path.exists(potential_path):
            file_path = potential_path
        else:
            # Try absolute path fallback (user's project root)
            base_dir = r"d:\Code\project_harvey\project-harvey-test"
            potential_path_2 = os.path.join(base_dir, "resumes", os.path.basename(file_path))
            if os.path.exists(potential_path_2):
                file_path = potential_path_2

    parser = ResumeParser()
    try:
        text = parser.parse(file_path)
    except Exception as e:
        return err(f"I encountered an issue parsing the resume: {e}")

    # Simple extraction fallback if not provided (in real app, use LLM here too)
    if not email:
        return err("Please provide the candidate's email address along with the resume.")
    
    if Candidate.objects.filter(email=email, organization=org).exists():
        return err(f"A candidate with the email '{email}' is already in the system.")

    c = Candidate.objects.create(
        organization=org,
        name=name or "Unknown Candidate",
        email=email,
        phone=phone,
        skills=[], 
        resume_file=file_path, 
        parsed_data=text,
        source="Resume Upload",
        status="pending",
    )
    
    return ok(f"I've successfully added {c.name} and attached their resume.", id=c.id, name=c.name)


@tool("list_candidates", return_direct=True)
def list_candidates(name: str = "", email: str = "", status: str = "", limit: int = 10, user=None) -> str:
    """
    Lists candidates with optional filters.
    Use this to search for candidates or see who has applied.
    """
    org = get_org(user)
    if not org:
        return err("User is not associated with any organization.")

    candidates = Candidate.objects.filter(organization=org)

    if name:
        candidates = candidates.filter(name__icontains=name)
    if email:
        candidates = candidates.filter(email__icontains=email)
    if status:
        candidates = candidates.filter(status__iexact=status)

    count = candidates.count()
    candidates = candidates.order_by("-created_at")[:limit]

    if count == 0:
        return ok("No candidates found matching your criteria.")

    # NLP-friendly output
    lines = [f"I found {count} candidate(s) (showing top {len(candidates)}):"]
    results = []
    
    for c in candidates:
        line = f"• {c.name} ({c.email}) - {c.status}"
        lines.append(line)
        results.append({"id": c.id, "name": c.name, "email": c.email, "status": c.status})

    return ok("\n".join(lines), results=results)


@tool("get_candidate_detail", return_direct=True)
def get_candidate_detail(candidate_id: int = None, email: str = None, user=None) -> str:
    """
    Retrieves detailed information about a specific candidate.
    Provide either candidate_id OR email.
    """
    org = get_org(user)
    if not org:
        return err("User is not associated with any organization.")

    c = None
    if candidate_id:
        c = Candidate.objects.filter(organization=org, id=candidate_id).first()
    elif email:
        c = Candidate.objects.filter(organization=org, email=email).first()

    if not c:
        return err("Candidate not found.")

    # Construct detail string
    skills_str = ", ".join(c.skills) if c.skills else "None listed"
    
    detail = [
        f"Candidate Profile: {c.name}",
        f" Email: {c.email}",
        f" Phone: {c.phone or 'N/A'}",
        f" Status: {c.status}",
        f" Skills: {skills_str}",
        f"Source: {c.source}",
    ]

    # Check for scores/applications
    scores = CandidateJobScore.objects.filter(candidate=c)
    if scores.exists():
        detail.append("\n**Job Applications & Scores:**")
        for s in scores:
            detail.append(f"- {s.job_role.title}: Score {s.score}/100")
            if s.justification:
                just = s.justification[:100] + "..." if len(s.justification) > 100 else s.justification
                detail.append(f"  *Insight: {just}*")

    return ok("\n".join(detail), id=c.id, name=c.name, email=c.email, full_data=str(c.__dict__))


@tool("shortlist_candidates", return_direct=True)
def shortlist_candidates(skills: str = "", job_role_id: int = None, limit: int = 5, user=None) -> str:
    """
    Shortlists candidates. 
    If job_role_id is provided, scores candidates against that role.
    Otherwise, filters by skills.
    """
    org = get_org(user)
    if not org:
        return err("User is not associated with any organization. Please contact support.")

    candidates = Candidate.objects.filter(organization=org)
    scored_results = []

    if job_role_id:
        try:
            job_role = JobRole.objects.get(id=job_role_id, organization=org)
            scorer = CandidateScorer()
            
            for c in candidates:
                # Check if score exists
                score_obj = CandidateJobScore.objects.filter(candidate=c, job_role=job_role).first()
                if score_obj:
                    score = score_obj.score
                    justification = score_obj.justification
                else:
                    # Compute score
                    score, justification = scorer.score_candidate(c, job_role)
                
                scored_results.append({
                    "id": c.id,
                    "name": c.name,
                    "score": score,
                    "justification": justification
                })
            
            # Sort by score desc
            scored_results.sort(key=lambda x: x["score"], reverse=True)
            scored_results = scored_results[:limit]
            
            msg = f"Here are the top {len(scored_results)} candidates for '{job_role.title}':"
            return ok(msg, results=scored_results)

        except JobRole.DoesNotExist:
            return err(f"Job Role with ID {job_role_id} not found.")
        except Exception as e:
            return err(f"Error scoring candidates: {e}")

    # Fallback to skills matching if no job role
    if not skills:
        return err("Please provide either a job_role_id or skills to shortlist.")

    skills_list = [s.strip().lower() for s in skills.split(",")]
    
    matched = [
        {"id": c.id, "name": c.name}
        for c in candidates
        if any(skill in (",".join(c.skills or [])).lower() for skill in skills_list)
    ]
    matched = matched[:limit]

    msg = f"I found the following candidates matching the skills: {', '.join(c['name'] for c in matched) or 'None found'}."
    return ok(msg, results=matched)
