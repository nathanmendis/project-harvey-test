from langchain.tools import tool
import json
from core.vector_store import get_vector_store

@tool
def search_policies(query: str, user=None) -> str:
    """
    Search for HR policies and procedures.
    Use this tool when the user asks about company rules, leave policies, benefits, code of conduct, etc.
    Returns relevant policy excerpts.
    """
    vector_store = get_vector_store()
    
    display_filter = {}
    if user and user.organization:
        # We need to construct the filter carefully. 
        # combining org_id AND doc_type='policy'
        display_filter = {
             "organization_id": str(user.organization.id),
             "doc_type": "policy"
        }
    else:
        display_filter = {"doc_type": "policy"}

    # We might want to filter by type='policy' if possible, but for now we rely on semantic search
    results = vector_store.similarity_search(query, k=3, filter=display_filter)
    
    if not results:
        return json.dumps({
            "ok": True,
            "message": "No relevant policies found."
        })
    
    formatted_results = []
    for doc in results:
        source = doc.metadata.get('source', 'Unknown Policy')
        formatted_results.append(f"Source: {source}\nContent: {doc.page_content}")

    return json.dumps({
        "ok": True,
        "message": "\n\n".join(formatted_results)
    })
