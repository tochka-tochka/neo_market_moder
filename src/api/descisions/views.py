import logging
import re
import uuid

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
from src.serializers import BlockReasonsMessageSerializer, TicketSummarySerializer


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
                    "code": "HARD_BLOCK",
                    "message": "Product is permanently blocked",
                },
                status=403,
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
                "idempotency_key": str(uuid.uuid4()),
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


def check_filed(data, field_str):
    tokens = re.findall(r"[^.\[\]]+", field_str)

    current = data
    for token in tokens:
        if token.isdigit():
            index = int(token)
            if isinstance(current, list) and 0 <= index < len(current):
                current = current[index]
            else:
                return False
        else:
            if isinstance(current, dict) and token in current:
                current = current[token]
            else:
                return False

    return True


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@parser_classes([JSONParser])
def decline_ticket(request, ticket_id):
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
                    "code": "HARD_BLOCK",
                    "message": "Product is permanently blocked",
                },
                status=403,
            )

        if ticket.status != TicketStatus.IN_REVIEW:
            return Response(
                {"code": "DECLINE_CONFLICT", "message": "Product is not in review"},
                status=409,
            )

        if ticket.assigned_moderator and ticket.assigned_moderator != request.user:
            return Response(
                {"code": "NOT_OWNER", "message": "Not assigned to you"}, status=403
            )

        blocking_reason_ids = request.data.get("blocking_reason_ids")
        moderator_comment = request.data.get("comment")
        field_reports_data = request.data.get("field_reports", [])

        blocking_reasons = []
        for id in blocking_reason_ids:
            blocking_reason = BlockReason.objects.filter(id=id).first()
            if blocking_reason is None:
                return Response(
                    {
                        "code": "WRONG_BLOCK_REASON_ID",
                        "message": "Blocking reason not found",
                    },
                    status=400,
                )
            ticket.status = (
                TicketStatus.HARD_BLOCKED
                if blocking_reason.hard_block
                else TicketStatus.BLOCKED
            )
            blocking_reasons.append(blocking_reason)

        if len(blocking_reasons) < 1:
            return Response(
                {
                    "code": "NO_BLOCK_REASONS",
                    "message": "must be at least 1 blocking reason",
                },
                status=400,
            )

        ticket.decision_at = timezone.now()
        ticket.decision_comment = moderator_comment
        ticket.save()

        ticket.blocking_reasons.add(*blocking_reasons)

        FieldReport.objects.filter(ticket=ticket).delete()

        for report_data in field_reports_data:
            if not check_filed(ticket.json_after, report_data["field_path"]):
                return Response(
                    {
                        "code": "WRONG_FIELD_PATH",
                        "message": f"Provided path {report_data['field_path']} invalid",
                    },
                    status=400,
                )
            FieldReport.objects.create(
                ticket=ticket,
                field_path=report_data.get("field_path"),
                message=report_data.get("message"),
                severity=report_data.get("severity"),
            )

        descision_queue.send_decision(
            data={
                "X-Service-Key": settings.B2B_SERVICE_KEY,
                "idempotency_key": str(uuid.uuid4()),
                "product_id": str(ticket.product_id),
                "status": "BLOCKED",
                "hard_block": ticket.status == TicketStatus.HARD_BLOCKED,
                "blocking_reason": BlockReasonsMessageSerializer(blocking_reasons[0]).data,
                "field_reports": field_reports_data,
            }
        )

        return Response(TicketSummarySerializer(ticket).data, status=200)

    except Exception:
        return Response({"code": "SERVER_ERROR"}, status=500)
