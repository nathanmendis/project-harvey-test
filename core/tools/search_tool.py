from langchain_core.tools import tool
from core.vector_store import get_vector_store

from core.tools.base import ok

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
    
    formatted_results = "\n\n".join(
        f"--- Result {i+1} ---\n{doc.page_content}" 
        for i, doc in enumerate(results)
    )
    return ok(f"Found the following information:\n{formatted_results}")
