from rest_framework import serializers
from src.models.moderation_queue import Queue, BlockReason

class QueueSerializer(serializers.ModelSerializer):
    class Meta:
        model = Queue
        fields = ["id", "product", "date"]

class BlockReasonsSerializer(serializers.ModelSerializer):
    class Meta:
        model=BlockReason
        fields = ["id", "reason"]