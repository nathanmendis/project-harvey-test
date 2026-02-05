
import os
import django
import json
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project_harvey.settings')
django.setup()

from core.tools.search_tool import search_knowledge_base
from core.tools.policy_search_tool import search_policies

def test_normalization():
    print("=== Testing Knowledge Base Normalization ===")
    kb_result = search_knowledge_base.invoke({"query": "steve"})
    kb_data = json.loads(kb_result)
    print(f"OK: {kb_data['ok']}")
    print("Message Output:")
    print(kb_data['message'])
    print("-" * 30)

    print("\n=== Testing Policy Normalization ===")
    policy_result = search_policies.invoke({"query": "leave policy"})
    policy_data = json.loads(policy_result)
    print(f"OK: {policy_data['ok']}")
    print("Message Output:")
    print(policy_data['message'])
    print("-" * 30)

if __name__ == '__main__':
    test_normalization()
