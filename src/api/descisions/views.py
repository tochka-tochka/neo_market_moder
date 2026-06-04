import logging

from django.conf import settings
from django.utils import timezone
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.parsers import JSONParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from interservice_queues.producer import descision_queue
from src.models.moderation import (
    BlockReason,
    FieldReport,
    Ticket,
    TicketStatus,
)
from src.serializers import TicketSummarySerializer


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@parser_classes([JSONParser])
def approve_ticket(request, ticket_id):
    try:
        ticket = Ticket.objects.filter(id=ticket_id).first()
        if ticket is None:
            return Response(
                {"code": "NOT_FOUND", "message": "Product moderation entry not found"},
                status=404,
            )

        if ticket.status == TicketStatus.HARD_BLOCKED:
            return Response(
                {
                    "code": "APPROVE_CONFLICT",
                    "message": "Product is permanently blocked",
                },
                status=409,
            )

        if ticket.status != TicketStatus.IN_REVIEW:
            return Response(
                {"code": "APPROVE_CONFLICT", "message": "Product is not in review"},
                status=409,
            )

        if ticket.assigned_moderator and ticket.assigned_moderator != request.user:
            return Response(
                {"code": "NOT_OWNER", "message": "Not assigned to you"}, status=403
            )

        if len(ticket.json_after["skus"]) == 0:
            return Response(
                {
                    "code": "APPROVE_CONFLICT",
                    "message": "Product has no SKUs, cannot approve",
                },
                status=409,
            )

        ticket.status = TicketStatus.MODERATED
        ticket.decision_at = timezone.now()
        ticket.decision_comment = request.data.get("comment")
        ticket.save()

        ticket.blocking_reasons.all().delete()

        FieldReport.objects.filter(ticket=ticket).delete()

        descision_queue.send_decision(
            data={
                "X-Service-Key": settings.B2B_SERVICE_KEY,
                "product_id": str(ticket.product_id),
                "status": TicketStatus.MODERATED,
            }
        )
        return Response(TicketSummarySerializer(ticket).data, status=200)

    except Exception as e:
        logging.info(f"Failed to approve product: {str(e)}")
        return Response(
            {"code": "SERVER_ERROR"},
            status=500,
        )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@parser_classes([JSONParser])
def decline_ticket(request, ticket_id):
    try:
        try:
            ticket = Ticket.objects.get(id=ticket_id)
        except Ticket.DoesNotExist:
            return Response(
                {"message": "Product moderation entry not found"}, status=404
            )

        if ticket.status == TicketStatus.HARD_BLOCKED:
            return Response({"message": "Product is permanently blocked"}, status=409)

        if ticket.status != TicketStatus.IN_REVIEW:
            return Response({"message": "Product is not in review"}, status=409)

        if ticket.assigned_moderator and ticket.assigned_moderator != request.user:
            return Response({"message": "Not assigned to you"}, status=403)

        blocking_reason_id = request.data.get("blocking_reason_id")
        moderator_comment = request.data.get("moderator_comment")
        field_reports_data = request.data.get("field_reports", [])

        blocking_reason = BlockReason.objects.filter(id=blocking_reason_id).first()
        if blocking_reason is None:
            return Response({"message": "Blocking reason not found"}, status=400)
        ticket.status = TicketStatus.HARD_BLOCKED
        ticket.decision_at = timezone.now()
        ticket.decision_comment = moderator_comment
        ticket.save()

        ticket.blocking_reasons.add(blocking_reason)

        FieldReport.objects.filter(ticket=ticket).delete()

        for report_data in field_reports_data:
            FieldReport.objects.create(
                ticket=ticket,
                field_name=report_data.get("field_name"),
                old_value=report_data.get("old_value"),
                new_value=report_data.get("new_value"),
            )

        descision_queue.send_decision(
            data={
                "X-Service-Key": settings.MOD_TO_B2B_KEY,
                "product_id": str(ticket.product_id),
                "status": TicketStatus.HARD_BLOCKED,
            }
        )

        return Response(TicketSummarySerializer(ticket).data, status=200)

    except Exception:
        return Response({"code": "SERVER_ERROR"}, status=500)
