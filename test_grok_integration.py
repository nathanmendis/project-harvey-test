
import os
import sys
import django

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project_harvey.settings")
django.setup()

from core.llm_graph.tools_registry import get_llm
from langchain_core.messages import HumanMessage

def test_grok():
    print("Testing Grok Integration...")
    try:
        llm = get_llm()
        print(f"LLM Initialized: {type(llm).__name__}")
        
        # specific check for Grok
        if hasattr(llm, 'openai_api_base'):
             print(f"Base URL: {llm.openai_api_base}")
        
        response = llm.invoke([HumanMessage(content="Hello, are you Grok?")])
        print(f"Response: {response.content}")
        print("SUCCESS: Grok integration verified.")
    except Exception as e:
        print(f"FAILURE: {e}")

if __name__ == "__main__":
    test_grok()
