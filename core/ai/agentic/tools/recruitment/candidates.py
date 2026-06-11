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

    # Fix: Resolve file path if it's a relative media path or a URL-like path
    if not os.path.exists(file_path):
        from django.conf import settings
        # If path starts with /media/, strip it and look in MEDIA_ROOT
        if file_path.startswith('/media/'):
            relative_path = file_path.replace('/media/', '')
            file_path = os.path.join(settings.MEDIA_ROOT, relative_path)
        elif 'media' in file_path and not os.path.isabs(file_path):
            # Try to find it relative to BASE_DIR if it's something like "media/resumes/..."
            from project_harvey.settings import BASE_DIR
            file_path = os.path.join(BASE_DIR, file_path)
            
    # Final Windows-style normalization
    file_path = os.path.abspath(file_path)

    parser = ResumeParser()
    try:
        text = parser.parse(file_path)
    except Exception as e:
        return err(f"I encountered an issue parsing the resume: {e}")

    # Intelligent extraction
    extracted = parser.extract_info(text)
    
    # Use provided values, fallback to extracted values
    name = name or extracted.get("name")
    email = email or extracted.get("email")
    skills = extracted.get("skills") if not phone else [] # Note: skills arg not in tool but we fill it in DB

    if not email:
        return err("Please provide the candidate's email address along with the resume.")
    
    if Candidate.objects.filter(email=email, organization=org).exists():
        return err(f"A candidate with the email '{email}' is already in the system.")

    from django.core.files import File
    
    with open(file_path, 'rb') as f:
        c = Candidate.objects.create(
            organization=org,
            name=name or "Unknown Candidate",
            email=email,
            phone=phone,
            skills=skills or [], 
            # We'll save the file in the next step to ensure clean naming
            parsed_data=text,
            source="Resume Upload",
            status="pending",
        )
        # Use only the filename, not the full path, to avoid Windows naming errors
        c.resume_file.save(os.path.basename(file_path), File(f), save=True)
    
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
    candidates = candidates.order_by("-id")[:limit]

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
        f" Source: {c.source}",
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
def shortlist_candidates(skills: str = "", job_role_id: str = "", limit: str = "5", user=None) -> str:
    """
    Shortlists candidates. 
    If job_role_id is provided, scores candidates against that role.
    Otherwise, filters by skills.
    Note: limit must be a number as a string.
    """
    org = get_org(user)
    if not org:
        return err("User is not associated with any organization. Please contact support.")

    candidates = Candidate.objects.filter(organization=org)
    scored_results = []

    # Handle limit conversion
    try:
        limit_int = int(limit)
    except:
        limit_int = 5

    if job_role_id:
        try:
            # Handle potential string or empty from LLM
            if not job_role_id or job_role_id == "null":
                return err("Please provide a valid job_role_id.")
            
            job_role_id_int = int(job_role_id)
            job_role = JobRole.objects.get(id=job_role_id_int, organization=org)
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
            
            # Filter by minimum threshold (e.g., 40) and sort by score desc
            scored_results = [r for r in scored_results if r["score"] >= 40]
            scored_results.sort(key=lambda x: x["score"], reverse=True)
            scored_results = scored_results[:limit_int]
            
            lines = [f"I've analyzed the candidates for the **{job_role.title}** role. Here are the top {len(scored_results)} matches based on their skills and experience:"]
            for r in scored_results:
                lines.append(f"\n- **{r['name']}** (Score: {r['score']}/100)")
                lines.append(f"  *Reasoning: {r['justification']}*")
            
            if not scored_results:
                return ok("I couldn't find any candidates in the system to evaluate for this role.")

            return ok("\n".join(lines), results=scored_results)

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
    matched = matched[:limit_int]

    if matched:
        msg = f"I've searched our database for candidates with skills in **{skills}**. Here is who I found:\n"
        for c in matched:
            msg += f"- {c['name']}\n"
    else:
        msg = f"I'm sorry, I couldn't find any candidates matching the skills: {skills}."
    
    return ok(msg, results=matched)
