from rest_framework import serializers, viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Policy
from core.services.policy_indexer import PolicyIndexer
import threading

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
