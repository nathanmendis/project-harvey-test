from langchain.tools import tool
import json
from core.ai.rag.vector_store import get_vector_store

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

    # 1. Intent Mapping for Section Scoring
    INTENT_SECTIONS = {
        "working hours": ["4. Working Hours and Attendance", "4.1 Working Hours"],
        "attendance": ["4. Working Hours and Attendance", "4.2 Attendance and Punctuality"],
        "late": ["4.2 Attendance and Punctuality", "11. Disciplinary Action"],
        "leave": ["5. Leave Policy", "5.1 Types of Leave", "12. Separation and Exit Policy"],
        "harassment": ["7. Workplace Harassment Policy"],
        "disciplinary": ["11. Disciplinary Action", "6. Code of Conduct"],
        "performance": ["8. Performance Management"],
        "promotion": ["8. Performance Management", "9. Compensation and Benefits"],
        "salary": ["9. Compensation and Benefits", "9.1 Salary"],
        "resignation": ["12. Separation and Exit Policy", "12.1 Resignation"],
        "termination": ["12. Separation and Exit Policy", "12.2 Termination", "11. Disciplinary Action"]
    }

    # Query Expansion (keep for better base retrieval)
    expansion_map = {
        "late": "late attendance punctuality discipline",
        "working hours": "working hours shift timing attendance",
        "salaries": "salary payment monthly compensation",
        "intern": "internship intern stipend"
    }
    expanded_query = query
    for word, expansion in expansion_map.items():
        if word.lower() in query.lower():
            expanded_query += f" {expansion}"

    import logging
    logger = logging.getLogger("harvey")
    logger.info(f"Searching policies for: '{query}' (Expanded: '{expanded_query}')")

    # 2. Base Retrieval (Increase K to ensure scoring captures specific sections)
    results = vector_store.similarity_search(expanded_query, k=15, filter=display_filter)
    
    if not results:
        return json.dumps({"ok": True, "message": "The policy does not specify information regarding this query."})

    # 3. Intent-to-Section Scoring
    def get_doc_score(doc, user_query):
        score = 0
        content = doc.page_content.lower()
        title = doc.metadata.get("title", "").lower()
        
        # Match intents from map
        for key, sections in INTENT_SECTIONS.items():
            if key in user_query.lower():
                for section in sections:
                    s_lower = section.lower()
                    if s_lower in content:
                        # High priority for matches near the start (likely a header in micro-chunk)
                        if s_lower in content[:100]:
                            score += 10
                        else:
                            score += 5
        
        # Penalize generic boilerplate
        if "purpose and scope" in content or "harvey effective date" in content:
            score -= 5
            
        return score

    scored_results = sorted(results, key=lambda d: get_doc_score(d, query), reverse=True)
    final_docs = scored_results[:3]

    # 4. Answerability Gate (Pre-LLM)
    # Refined Check: Look for numbers that aren't just section headers (e.g., "5.1")
    def has_meaningful_numbers(text):
        # Find all numbers
        nums = re.findall(r"\d+", text)
        # 8 and 9 are common working hours. 10+ are common leave days.
        # Section numbers 1-14 are common. 
        # Better: keep digits that aren't JUST section markers.
        # For now, let's allow anything > 7, as shift hours are 8 or 9.
        meaningful_nums = [n for n in nums if int(n) >= 8] 
        if meaningful_nums: return True
        return len(nums) > 10 # High density of small numbers usually means a table or list
    
    quantitative_keywords = ["how many", "how much", "how often", "days", "hours", "count", "period"]
    if any(k in query.lower() for k in quantitative_keywords):
        # Need to import re for has_meaningful_numbers
        import re
        # Combine all page content for a comprehensive check
        context_text = " ".join([d.page_content for d in final_docs])
        if not has_meaningful_numbers(context_text):
            logger.info("Answerability Gate: No meaningful digits found for quantitative query. Short-circuiting.")
            return json.dumps({"ok": True, "message": "The policy mentions the relevant section but does not specify the exact number, duration, or frequency for this request."})

    formatted_results = [f"Source: {d.metadata.get('title', 'Unknown')}\nExcerpt: {' '.join(d.page_content.split())}" for d in final_docs]
    context = "\n\n".join(formatted_results)

    # 5. Professional LLM Rephrasing
    from core.ai.agentic.graph.tools_registry import get_lite_llm
    from langchain_core.prompts import ChatPromptTemplate
    
    llm = get_lite_llm()
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a strict HR Assistant. Answer using ONLY the provided excerpts.
        
STRICT RULES:
1. NO INFERENCE: If a value (number, name, count) is not in the text, say "The policy does not specify this."
2. VERBATIM NUMBERS: Any number in your answer must exist in the excerpts.
3. DIRECTNESS: Prefer short, direct answers. Do not rephrase beyond what is explicitly stated.
4. AMBIGUITY: If the query is about a choice or conflict not defined, say "The policy does not explicitly define this."
5. NO LEGAL ADVICE: Redirect harassment/legal queries to HR or the Internal Complaints Committee (ICC)."""),
        ("user", "User Question: {query}\n\nExcerpts:\n{context}")
    ])
    
    chain = prompt | llm
    try:
        response = chain.invoke({"query": query, "context": context})
        answer = response.content
        
        # 6. Post-Answer Numeric Auto-Grader
        import re
        nums_answer = re.findall(r"\d+", answer)
        if nums_answer:
            nums_context = re.findall(r"\d+", context)
            if not set(nums_answer).issubset(set(nums_context)):
                logger.warning(f"Auto-Grader: Hallucinated numbers detected: {nums_answer}. Fallback applied.")
                return json.dumps({"ok": True, "message": "The policy mentions relevant sections but does not specify exact numbers or durations for this request."})
        
        message = answer
    except Exception as e:
        logger.error(f"Lite NLP (1B) failed: {e}")
        message = "I found relevant sections but had an error rephrasing. Please refer to: " + "\n\n".join(formatted_results)

    return json.dumps({
        "ok": True,
        "message": message
    })
