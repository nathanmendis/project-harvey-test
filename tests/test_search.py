import os
import django
import sys

# Setup Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project_harvey.settings')
django.setup()

from core.tools.search_tool import search_knowledge_base

def test_search():
    print("--- Testing Semantic Search ---")
    
    # Query 1: Find candidate by name
    query1 = "Find candidate Nathan"
    print(f"\nQuery: {query1}")
    result1 = search_knowledge_base.invoke({"query": query1})
    print(f"Result:\n{result1}")

    # Query 2: Find candidate by skill
    query2 = "Who knows Python?"
    print(f"\nQuery: {query2}")
    result2 = search_knowledge_base.invoke({"query": query2})
    print(f"Result:\n{result2}")

if __name__ == "__main__":
    test_search()
