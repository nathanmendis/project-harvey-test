
import os
import django
import json
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project_harvey.settings')
django.setup()

from core.tools.policy_search_tool import search_policies

def test_lite_nlp():
    print("=== Testing Lite NLP Policy Normalization (1B) ===")
    policy_result = search_policies.invoke({"query": "leave policy"})
    policy_data = json.loads(policy_result)
    print(f"OK: {policy_data['ok']}")
    print("Conversational Output:")
    print(policy_data['message'])
    print("-" * 30)

if __name__ == '__main__':
    test_lite_nlp()
