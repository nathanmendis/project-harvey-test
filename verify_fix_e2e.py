import os
import django
import sys

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project_harvey.settings')
django.setup()

from core.tools.search_tool import search_knowledge_base
from core.tools.policy_search_tool import search_policies

def verify_fix():
    print("--- Verifying Candidate Search ---")
    # This query "Steve developer Project Harvey" previously returned HR policies.
    # Now it should strictly return candidates.
    query = "Steve developer Project Harvey"
    result = search_knowledge_base.invoke({"query": query})
    print(f"Query: {query}")
    print(f"Result:\n{result}")
    
    if "Human Resources Policy Manual" in result:
        print("\n❌ FAILURE: HR Policy found in candidate search results!")
    else:
        print("\n✅ SUCCESS: No HR Policies in candidate search.")

    print("\n--- Verifying Policy Search ---")
    policy_query = "Leave policy"
    policy_result = search_policies.invoke({"query": policy_query})
    print(f"Query: {policy_query}")
    print(f"Result:\n{policy_result}")
    
    if "No relevant policies found" in policy_result:
        print("\n⚠️ WARNING: No policies found. Check if indexing worked or if query matches.")
    else:
        print("\n✅ SUCCESS: Policy search returned results.")

if __name__ == "__main__":
    verify_fix()
