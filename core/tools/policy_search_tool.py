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
        source = doc.metadata.get('title', doc.metadata.get('source', 'Unknown Policy'))
        # Clean up excessive whitespace in content
        content = " ".join(doc.page_content.split())
        formatted_results.append(f"Source: {source}\nExcerpt: {content}")

    # Use Lite LLM (1B) to normalize into NLP
    from core.llm_graph.tools_registry import get_lite_llm
    from langchain_core.prompts import ChatPromptTemplate
    
    llm = get_lite_llm()
    context = "\n\n".join(formatted_results)
    
    prompt = ChatPromptTemplate.from_template("""
    You are an HR Assistant. Based ONLY on the excerpts below, provide a professional and concise answer to the user's question.
    If the excerpts don't contain the answer, say you don't know based on company policy.
    
    User Question: {query}
    
    Excerpts:
    {context}
    
    Direct Answer:
    """)
    
    chain = prompt | llm
    try:
        response = chain.invoke({"query": query, "context": context})
        message = response.content
    except Exception as e:
        # Fallback to template if API fails
        from core.llm_graph.nodes import logger
        logger.error(f"Lite NLP (1B) rephrasing failed: {e}")
        message = "I found the following relevant policy excerpts:\n\n" + "\n\n".join(formatted_results)

    return json.dumps({
        "ok": True,
        "message": message
    })
