from langchain_core.tools import tool
from core.ai.rag.vector_store import get_vector_store
from core.ai.agentic.tools.utils import ok

@tool
def search_knowledge_base(query: str, user=None):
    """
    Searches the internal knowledge base for candidates, job roles, and other indexed information.
    Use this to find people with specific skills or details about job openings.
    """
    store = get_vector_store()
    # Filter for candidates and jobs
    filter_spec = {"doc_type": {"$in": ["candidate", "job"]}}
    results = store.similarity_search(query, k=3, filter=filter_spec)
    
    if not results:
        return ok("No relevant information found in the knowledge base.")
    
    formatted_results = []
    for i, doc in enumerate(results):
        m = doc.metadata
        dtype = m.get("doc_type", "unknown")
        
        if dtype == "candidate":
            name = m.get("name", "Unknown Candidate")
            email = m.get("email", "No Email")
            skills = m.get("skills", "No Skills listed")
            formatted_results.append(f"- **{name}** ({email}) | Skills: {skills}")
        elif dtype == "job":
            title = m.get("title", "Unknown Job")
            dept = m.get("department", "General")
            formatted_results.append(f"- **{title}** [{dept}]")
        else:
            source = m.get("source", "Unknown Source")
            formatted_results.append(f"- **{source}**: {doc.page_content[:150]}...")

    message = "I found the following matches in the knowledge base:\n\n" + "\n".join(formatted_results)
    return ok(message)
