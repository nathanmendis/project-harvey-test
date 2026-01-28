
import os
import django
import sys

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project_harvey.settings")
django.setup()

from django.contrib.auth import get_user_model

def list_users():
    User = get_user_model()
    users = User.objects.all()
    print(f"Found {users.count()} users:")
    for u in users:
        print(f"- Username: {u.username}, Role: {getattr(u, 'role', 'N/A')}, Superuser: {u.is_superuser}")

if __name__ == "__main__":
    list_users()
