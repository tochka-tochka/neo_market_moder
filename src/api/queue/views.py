from django.db import transaction
from datetime import timedelta, datetime

from django.db.models import Q
from django.utils import timezone
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.parsers import JSONParser
from rest_framework.permissions import IsAuthenticated

from rest_framework.response import Response

from src.models.moderation import Ticket, TicketStatus
from src.serializers import TicketSerializer


class NotFoundException(Exception):
    pass


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@parser_classes([JSONParser])
@transaction.atomic
def get_next_product(request):
    try:
        if Ticket.objects.filter(assigned_moderator=request.user).first() is not None:
            return Response(
                {
                    "code": "MODER_TICKET_CONFLICT",
                    "message": "autheficated moderator alreda have ticket",
                },
                status=409,
            )
        queue = Q(status=TicketStatus.PENDING)
        if "queue_priority" in request.data:
            if not (1 <= request.data["queue_priority"] <= 4):
                return Response(
                    {"code": "INVALID_QUEUE", "message": "invalid queue_priority value"}, status=400
                )
            queue &= Q(queue_priority=request.data["queue_priority"])

        next = Ticket.objects.select_for_update(skip_locked=True).filter(queue).first()

        if next is None:
            return Response(
                {"code": "NO_CONTENT", "message": "no products in queue"}, status=204
            )

        next.status = TicketStatus.IN_REVIEW
        next.claimed_at = timezone.now()
        next.claim_expires_at = timezone.make_aware(datetime.now() + timedelta(minutes=30))
        next.assigned_moderator = request.user
        next.save()
        

        return Response(TicketSerializer(next).data)
    except Exception as e:
        return Response({"message": f"failed to get next product: {e}"}, status=500)
