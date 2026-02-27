import os
import django
import sys

# Setup Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project_harvey.settings")
django.setup()

from core.ai.rag.tools.search_tool import search_knowledge_base

def run_tests():
    print("========================================")
    print("🧪 Testing RAG Candidate Search Fix 🧪")
    print("========================================")
    
    queries = [
        "who is Madhuri ",
        "do you know Jatin Gokhale",
        "find candidate named Akshay",
        "tell me about Mohan Pillai"
    ]
    
    for q in queries:
        print(f"\n[QUERY]: '{q}'")
        try:
            # Call the tool directly, bypassing the graph and LLM
            # The tool expects a dictionary with 'query' and optionally 'user'
            result = search_knowledge_base.invoke({"query": q})
            print("[RESULT]:\n" + result)
        except Exception as e:
            print(f"[ERROR]: {e}")
            
    print("\n========================================")
    print("✅ Test Complete!")
    print("========================================")

if __name__ == "__main__":
    run_tests()
