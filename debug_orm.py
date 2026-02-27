import os
import django
import sys

# Setup Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project_harvey.settings")
django.setup()

from core.models.recruitment import Candidate

def debug_query():
    qs = Candidate.objects.filter(name__icontains="Madhuri")
    print(f"Candidates with 'Madhuri': {qs.count()}")
    for c in qs:
        print(f" - {c.name} ({c.email})")

    qs_solanki = Candidate.objects.filter(name__icontains="Solanki")
    print(f"\nCandidates with 'Solanki': {qs_solanki.count()}")
    for c in qs_solanki:
        print(f" - {c.name} ({c.email})")

if __name__ == "__main__":
    debug_query()
