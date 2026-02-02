from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field
from typing import Optional, Dict, List
from .tools_registry import get_reasoner_llm
import json
import logging

logger = logging.getLogger("harvey")

class ContextUpdate(BaseModel):
    current_goal: Optional[str] = Field(description="The current active goal of the user")
    extracted_info: Dict[str, str] = Field(description="Key-value pairs of extracted information relevant to the goal")
    last_active_topic: Optional[str] = Field(description="The general topic of the conversation")
    topic_shift: bool = Field(description="True if the user just changed the topic")

SUMMARY_TEMPLATE = """Analyze the conversation history and update the context.
Return a JSON object with the following fields:
- current_goal: What the user is trying to achieve right now.
- extracted_info: specific details (names, dates, etc.) mentioned.
- last_active_topic: The general topic (e.g., "recruiting", "leave_policy").
- topic_shift: Boolean, true if the topic changed recently.

If there is no meaningful context, return empty fields.

History:
{history}
"""

def summarize(messages) -> Dict:
    if len(messages) < 2:
        return {}
    
    llm = get_reasoner_llm()
    # Include more history for better context
    text = "\n".join(f"{m.type}: {m.content}" for m in messages[-20:])

    parser = JsonOutputParser(pydantic_object=ContextUpdate)

    chain = (
        ChatPromptTemplate.from_template(SUMMARY_TEMPLATE)
        | llm
        | parser
    )

    try:
        out = chain.invoke({"history": text})
        return out
    except Exception as e:
        logger.error(f"Summarization failed: {e}")
        return {}
