from django.db import models
from .organization import Organization, User
import uuid

class Conversation(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=255, default="New Chat")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    context_state = models.JSONField(default=dict, blank=True)
    memory_state = models.JSONField(default=dict, blank=True) 

    def __str__(self):
        return f"{self.title} ({self.user.username})"


class Message(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE)
    sender = models.CharField(max_length=10)  # 'user' or 'ai'
    message_text = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.sender.capitalize()} → {self.message_text[:40]}"


class GraphRun(models.Model):
    STATUS_CHOICES = [
        ("running", "Running"),
        ("success", "Success"),
        ("error", "Error"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="graph_runs")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="graph_runs")

    input_text = models.TextField()
    output_text = models.TextField(blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="running")
    error_message = models.TextField(blank=True)

    trace = models.JSONField(default=list, blank=True)  # list of node events

    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Run {self.id} ({self.status}) for {self.user.username}"
