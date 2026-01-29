
import os
import sys
import django

sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project_harvey.settings")
django.setup()

from core.models.policy import Policy
from core.vector_store import get_vector_store

def clean_policies():
    print("--- Active Policies ---")
    policies = Policy.objects.all()
    for p in policies:
        print(f"ID: {p.id} | Title: {p.title} | Status: {p.status}")
        # We can also check content if needed, but title is usually unique enough for tests
        if p.title == "Test Leave Policy":
            print(f" -> FOUND POLLUTING TEST DATA: {p.title}. Deleting...")
            p.delete()
            # Note: signal handlers usually remove from vector store if implemented, 
            # otherwise we might need to verify vector store cleanup.
            # Assuming our app handles cleanup or we might need to re-index.
            print(" -> Deleted.")
    
    print("--- Remaining Policies ---")
    for p in Policy.objects.all():
        print(f"ID: {p.id} | Title: {p.title}")

if __name__ == "__main__":
    clean_policies()
