import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project_harvey.settings')
django.setup()

from django.db import connection
from core.models.recruitment import Interview

def fix_sequence():
    table_name = Interview._meta.db_table
    print(f"Checking sequence for table: {table_name}")
    
    with connection.cursor() as cursor:
        # Get the max ID
        max_id = Interview.objects.order_by("-id").first().id if Interview.objects.exists() else 0
        print(f"Current Max ID: {max_id}")
        
        # Reset the sequence
        # PostgreSQL syntax for resetting sequence
        seq_name = f"{table_name}_id_seq"
        cursor.execute(f"SELECT setval('{seq_name}', %s, true);", [max_id])
        
        new_val = cursor.fetchone()[0]
        print(f"Sequence {seq_name} reset to: {new_val}")

if __name__ == "__main__":
    fix_sequence()
