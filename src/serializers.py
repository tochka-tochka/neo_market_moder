from django.contrib.auth.models import User
from rest_framework import serializers

from src.models.moderation import BlockReason, Decision, Ticket


class BlockReasonsSerializer(serializers.ModelSerializer):
    class Meta:
        model = BlockReason
        fields = [
            "id",
            "code",
            "title",
            "description",
            "hard_block",
            "is_active",
        ]

class BlockReasonsMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = BlockReason
        fields = [
            "id",
            "title",
            "description",
        ]

class DecisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Decision
        fields = ["id", "action", "comment", "at"]


class TicketSerializer(serializers.ModelSerializer):
    assigned_moderator_id = serializers.UUIDField(source="assigned_moderator.id", read_only=True)
    blocking_reasons = BlockReasonsSerializer(source="blocking_reason", read_only=True, many=True)
    history = DecisionSerializer(read_only=True, many=True)

    class Meta:
        model = Ticket
        fields = [
            "id",
            "product_id",
            "seller_id",
            "kind",
            "status",
            "queue_priority",
            "json_before",
            "json_after",
            "created_at",
            "updated_at",
            "decision_at",
            "claimed_at",
            "claim_expires_at",
            "assigned_moderator_id",
            "decision_comment",
            "blocking_reasons",
            "history",
        ]

class TicketSummarySerializer(serializers.ModelSerializer):
    assigned_moderator_id = serializers.UUIDField(source="assigned_moderator.id", read_only=True)

    class Meta:
        model = Ticket
        fields = [
            "id",
            "product_id",
            "seller_id",
            "kind",
            "status",
            "queue_priority",
            "created_at",
            "updated_at",
            "decision_at",
            "claimed_at",
            "claim_expires_at",
            "assigned_moderator_id",
        ]


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ("username", "email", "password")

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data["username"],
            email=validated_data.get("email", ""),
            password=validated_data["password"],
        )
        return user
