from langchain_core.tools import tool
from core.ai.rag.vector_store import get_vector_store
from core.ai.agentic.tools.utils import ok

@tool
def search_knowledge_base(query: str, user=None):
    """
    Searches the internal knowledge base for candidates, job roles, and other indexed information.
    Use this to find people with specific skills or details about job openings.
    """
    # 1. Exact Match Fallback for Candidates
    # Because semantic search often groups Indian names closely (e.g. Madhuri Solanki vs Madhuri Kulkarni),
    # we first check if there's an exact Candidate name match in the DB.
    exact_candidates = []
    try:
        from core.models.recruitment import Candidate
        from django.db.models import Q
        import re
        
        # Remove common question filler words so we're left with just the name
        clean_query = re.sub(r'(?i)\b(who|is|do|you|know|about|find|search|for|tell|me|can|candidate)\b', '', query).strip()
        words = clean_query.split()
        
        if words:
            qs = Candidate.objects.all()
            if user and user.organization:
                qs = qs.filter(organization=user.organization)
            
            # 1. Try matching the exact cleaned phrase first
            matched_qs = qs.filter(name__icontains=clean_query)
            
            # 2. If exact phrase match didn't yield anything and we have multiple words, try ANDing the words (e.g. "Madhuri" AND "Solank")
            if not matched_qs.exists() and len(words) > 1:
                q_obj = Q()
                for w in words:
                    if len(w) >= 3:
                        if not q_obj:
                            q_obj = Q(name__icontains=w)
                        else:
                            q_obj &= Q(name__icontains=w)
                
                if q_obj:
                    matched_qs = qs.filter(q_obj)
            
            if matched_qs.exists():
                # Get candidates that match the exact phrase or all words
                for c in matched_qs[:2]:
                    # skills is a JSONField, usually holding a list of strings
                    skills_val = getattr(c, 'skills', []) or []
                    if isinstance(skills_val, list):
                        skills = ", ".join(str(s) for s in skills_val)
                    else:
                        skills = str(skills_val)
                        
                    exact_candidates.append({
                        "type": "candidate",
                        "name": c.name,
                        "email": c.email,
                        "skills": skills or "No Skills listed"
                    })
    except Exception as e:
        import logging
        logging.getLogger("harvey").error(f"Search Tool ORM fallback error: {e}")

    # 2. Vector Search Fallback
    store = get_vector_store()
    filter_spec = {"doc_type": {"$in": ["candidate", "job"]}}
    results = store.similarity_search(query, k=3, filter=filter_spec)
    
    if not results and not exact_candidates:
        return ok("No relevant information found in the knowledge base.")
    
    formatted_results = []
    seen = set()
    
    # Prepend exact candidates first so they are strongly weighted and bypass duplicate filtering
    for ec in exact_candidates:
        if ec["email"] not in seen:
            seen.add(ec["email"])
            formatted_results.append(f"- ✅ Exact Candidate Match: **{ec['name']}** ({ec['email']}) | Skills: {ec['skills']}")
    
    for doc in results:
        m = doc.metadata
        dtype = m.get("doc_type", "unknown")
        
        if dtype == "candidate":
            name = m.get("name", "Unknown Candidate")
            email = m.get("email", "No Email")
            if email in seen: continue
            seen.add(email)
            
            skills = m.get("skills", "No Skills listed")
            formatted_results.append(f"- Candidate: **{name}** ({email}) | Skills: {skills}")
            
        elif dtype == "job":
            title = m.get("title", "Unknown Job")
            dept = m.get("department", "General")
            key = f"{title}_{dept}"
            if key in seen: continue
            seen.add(key)
            
            formatted_results.append(f"- Job Role: **{title}** [{dept}]")
            
        else:
            source = m.get("source", "Unknown Source")
            content_hash = hash(doc.page_content.strip())
            if content_hash in seen: continue
            seen.add(content_hash)
            
            formatted_results.append(f"- **{source}**: {doc.page_content[:150]}...")

    message = "I found the following matches in the knowledge base:\n\n" + "\n".join(formatted_results)
    return ok(message)

