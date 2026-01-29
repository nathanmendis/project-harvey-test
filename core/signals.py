
import os

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from core.models.policy import Policy
from core.models.recruitment import Candidate, JobRole
from core.services.model_indexer import ModelIndexer
import threading

@receiver(post_delete, sender=Policy)
def delete_policy_file(sender, instance, **kwargs):
    """
    Deletes the file from the filesystem when the Policy object is deleted.
    """
    if instance.uploaded_file:
        if os.path.isfile(instance.uploaded_file.path):
            try:
                os.remove(instance.uploaded_file.path)
                print(f"🗑️ Deleted file: {instance.uploaded_file.path}")
            except Exception as e:
                print(f"⚠️ Error deleting file: {e}")

@receiver(post_save, sender=Candidate)
def index_candidate_on_save(sender, instance, created, **kwargs):
    """
    Triggers indexing when a Candidate is saved (created or updated).
    Runs in a background thread to avoid blocking.
    """
    def _index():
        indexer = ModelIndexer()
        indexer.index_candidate(instance.id)

    threading.Thread(target=_index).start()

@receiver(post_save, sender=JobRole)
def index_job_role_on_save(sender, instance, created, **kwargs):
    """
    Triggers indexing when a JobRole is saved.
    """
    def _index():
        indexer = ModelIndexer()
        indexer.index_job_role(instance.id)
        
    threading.Thread(target=_index).start()

