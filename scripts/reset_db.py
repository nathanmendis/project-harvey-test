
import os
import sys
import django
from django.db import connection
from django.conf import settings


sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project_harvey.settings")
django.setup()

from core.models.policy import Policy
from core.models.chatbot import Conversation, Message

def reset():
    print("⚠️  STARTING DATABASE RESET ⚠️")
    
    # 1. Clear Django Models
    deleted_policies, _ = Policy.objects.all().delete()
    print(f"✅ Deleted {deleted_policies} Policy objects.")
    
    deleted_convos, _ = Conversation.objects.all().delete()
    print(f"✅ Deleted {deleted_convos} Conversation objects (and related Messages).")
    
    # 2. Clear Vector Store tables (Raw SQL)
    # LangChain PGVector uses 'langchain_pg_embedding' and 'langchain_pg_collection'
    with connection.cursor() as cursor:
        try:
            print("⏳ Clearing Vector Store tables...")
            cursor.execute("TRUNCATE TABLE langchain_pg_embedding CASCADE;")
            cursor.execute("TRUNCATE TABLE langchain_pg_collection CASCADE;")
            print("✅ Truncated vector store tables (langchain_pg_embedding, langchain_pg_collection).")
        except Exception as e:
            print(f"⚠️  Warning clearing vector tables (might not exist yet): {e}")

    # 3. Clear Media Files (Policies)
    import shutil
    media_path = os.path.join(settings.MEDIA_ROOT, 'policies')
    if os.path.exists(media_path):
        try:
            shutil.rmtree(media_path)
            os.makedirs(media_path, exist_ok=True)
            print(f"✅ Cleared media directory: {media_path}")
        except Exception as e:
            print(f"⚠️  Warning clearing media files: {e}")
            
    print("\n🎉 Database reset complete. The system is clean.")

if __name__ == "__main__":
    reset()
