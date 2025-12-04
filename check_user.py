import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project_harvey.settings')
django.setup()

from core.models.recruitment import Candidate

def check_user():
    print("Checking for CANDIDATES with 'nathan' in name...")
    candidates = Candidate.objects.filter(name__icontains='nathan')
    
    if candidates.exists():
        for c in candidates:
            print(f"Found Candidate: ID={c.id}, Name={c.name}, Email={c.email}, Status={c.status}")
    else:
        print("No candidate found with name 'nathan'.")

if __name__ == "__main__":
    check_user()
