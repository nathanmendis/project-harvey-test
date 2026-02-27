import os
from django.db.models.signals import post_delete
from django.dispatch import receiver
from core.models.policy import Policy


@receiver(post_delete, sender=Policy)
def delete_policy_file(sender, instance, **kwargs):
    """
    Deletes the uploaded file from the filesystem when a Policy is deleted.
    Candidate / JobRole indexing is handled by the Celery periodic task
    (core.tasks.index_candidates_and_jobs) which runs every 2 hours.
    """
    if instance.uploaded_file:
        if os.path.isfile(instance.uploaded_file.path):
            try:
                os.remove(instance.uploaded_file.path)
                print(f"Ὕ1️ Deleted file: {instance.uploaded_file.path}")
            except Exception as e:
                print(f"⚠️ Error deleting file: {e}")
