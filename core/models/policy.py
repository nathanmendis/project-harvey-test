from django.db import models
from .organization import User
import uuid

class Policy(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("indexing", "Indexing"),
        ("indexed", "Indexed"),
        ("failed", "Failed"),
    ]
    SOURCE_CHOICES = [
        ("upload", "File Upload"),
        ("url", "External URL"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    
    uploaded_file = models.FileField(upload_to='policies/', null=True, blank=True)
    external_url = models.URLField(null=True, blank=True)
    source_type = models.CharField(max_length=10, choices=SOURCE_CHOICES)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    indexed_at = models.DateTimeField(null=True, blank=True)
    
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="policies")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    metadata = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return self.title


class PolicyChunk(models.Model):
    policy = models.ForeignKey(Policy, on_delete=models.CASCADE, related_name="chunks")
    chunk_index = models.PositiveIntegerField()
    text = models.TextField()
    vector_id = models.CharField(max_length=100, null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["chunk_index"]

    def __str__(self):
        return f"{self.policy.title} - Chunk {self.chunk_index}"
