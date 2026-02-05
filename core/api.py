from rest_framework import serializers, viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Policy, Conversation, Message
from core.ai.rag.policy_indexer import PolicyIndexer
import threading
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator

class PolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = Policy
        fields = '__all__'
        read_only_fields = ('id', 'created_by', 'created_at', 'updated_at', 'status', 'indexed_at')

class PolicyViewSet(viewsets.ModelViewSet):
    queryset = Policy.objects.all()
    serializer_class = PolicySerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['post'])
    def index(self, request, pk=None):
        policy = self.get_object()
        indexer = PolicyIndexer()
        # Run in thread
        thread = threading.Thread(target=indexer.index_policy, args=(policy.id,))
        thread.start()
        return Response({'status': 'indexing started'}, status=status.HTTP_202_ACCEPTED)


# --- Multiple Conversations API ---

@login_required
def list_conversations(request):
    """
    Returns a JSON list of all conversations for the current user,
    ordered by most recently updated.
    """
    conversations = Conversation.objects.filter(
        user=request.user
    ).order_by('-updated_at').values('id', 'title', 'updated_at')
    
    return JsonResponse({"conversations": list(conversations)})


@login_required
def get_conversation_messages(request, conversation_id):
    """
    Returns paginated messages for a conversation.
    Offset: Number of messages to skip from the end (reverse chronological).
    Limit: Number of messages to return.
    """
    try:
        # Verify ownership
        convo = Conversation.objects.get(id=conversation_id, user=request.user)
    except Conversation.DoesNotExist:
        return JsonResponse({"error": "Conversation not found"}, status=404)

    limit = int(request.GET.get("limit", 20))
    offset = int(request.GET.get("offset", 0))

    # Fetch messages sorted by timestamp DESC (newest first) with ID tiebreaker
    all_messages = Message.objects.filter(conversation=convo).order_by('-timestamp', '-id')
    
    # Slice the query
    messages_slice = all_messages[offset : offset + limit]
    
    # Check if there are more
    total_count = all_messages.count()
    has_more = (offset + limit) < total_count

    data = []
    # Reverse back to Oldest -> Newest for display
    for msg in reversed(messages_slice):
        data.append({
            "sender": msg.sender,
            "text": msg.text,  # Use decrypted property
            "timestamp": msg.timestamp.isoformat()
        })

    return JsonResponse({
        "messages": data,
        "has_more": has_more,
        "title": convo.title
    })

@csrf_exempt
@login_required
@require_http_methods(["DELETE", "POST"])
def delete_conversation(request, conversation_id):
    """
    Delete a specific conversation.
    """
    try:
        convo = Conversation.objects.get(id=conversation_id, user=request.user)
        convo.delete()
        return JsonResponse({"status": "success", "message": "Conversation deleted"})
    except Conversation.DoesNotExist:
        return JsonResponse({"error": "Conversation not found"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
