import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project_harvey.settings')
django.setup()

from core.models.policy import Policy
from core.ai.rag.policy_indexer import PolicyIndexer

def reindex():
    # Find the main HR policy
    policy = Policy.objects.filter(title__icontains="Human Resources Policy Manual").first()
    if not policy:
        print("Policy not found in DB")
        return
    
    print(f"Found Policy: {policy.title} (ID: {policy.id})")
    
    indexer = PolicyIndexer()
    print("Clearing old vectors...")
    indexer.vector_store.delete_all()
    
    print("Starting re-indexing with micro-chunks...")
    success = indexer.index_policy(policy.id)
    if success:
        print("✅ Re-indexing complete.")
    else:
        print("❌ Re-indexing failed.")

if __name__ == "__main__":
    reindex()
