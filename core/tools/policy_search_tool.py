from langchain.tools import tool
from core.vector_store import get_vector_store

@tool
def search_policies(query: str) -> str:
    """
    Search for HR policies and procedures.
    Use this tool when the user asks about company rules, leave policies, benefits, code of conduct, etc.
    Returns relevant policy excerpts.
    """
    vector_store = get_vector_store()
    # We might want to filter by type='policy' if possible, but for now we rely on semantic search
    results = vector_store.similarity_search(query, k=3)
    
    if not results:
        return "No relevant policies found."
    
    formatted_results = []
    for doc in results:
        source = doc.metadata.get('source', 'Unknown Policy')
        # Filter out non-policy results if they accidentally get mixed in (though separate index is better)
        # For now, we assume the index is shared or we just return what we find.
        # Ideally, we check doc.metadata.get('type') == 'policy'
        
        if doc.metadata.get('type') == 'policy':
            formatted_results.append(f"Source: {source}\nContent: {doc.page_content}")
        elif 'policy' in source.lower(): # Fallback heuristic
             formatted_results.append(f"Source: {source}\nContent: {doc.page_content}")

    if not formatted_results:
        # If strict filtering returns nothing, return raw results (maybe it's a mixed index)
        # Or just return "No policies found"
        # Let's be lenient for now as we are just starting
        for doc in results:
             source = doc.metadata.get('source', 'Unknown')
             formatted_results.append(f"Source: {source}\nContent: {doc.page_content}")

    return "\n\n".join(formatted_results)
