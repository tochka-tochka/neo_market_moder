from datetime import datetime

from django.conf import settings
from rest_framework.decorators import api_view
from rest_framework.response import Response

from interservice_queues.producer import descision_queue
from src.models.moderation import (
    BlockReason,
    FieldReport,
    Ticket,
    TicketStatus,
)


@api_view(["POST"])
def approve_ticket(request, ticket_id):
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

        if (
            ticket.assigned_moderator
            and ticket.assigned_moderator != request.user
        ):
            return Response({"message": "Not assigned to you"}, status=403)

        ticket.status = TicketStatus.MODERATED
        ticket.decision_at = datetime.now()
        ticket.moderator_comment = request.data.get("moderator_comment")
        ticket.blocking_reason = None
        ticket.save()

        FieldReport.objects.filter(ticket=ticket).delete()

        descision_queue.send_decision(
            data={
                "X-Service-Key": settings.MOD_TO_B2B_KEY,
                "product_id": str(ticket.product_id),
                "status": TicketStatus.MODERATED,
            }
        )

        return Response({"message": "Product approved successfully"}, status=200)

    except Exception as e:
        return Response({"message": f"Failed to approve product: {e}"}, status=500)


@api_view(["POST"])
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

        if (
            ticket.assigned_moderator
            and ticket.assigned_moderator != request.user
        ):
            return Response({"message": "Not assigned to you"}, status=403)

        blocking_reason_id = request.data.get("blocking_reason_id")
        moderator_comment = request.data.get("moderator_comment")
        field_reports_data = request.data.get("field_reports", [])

        blocking_reason = BlockReason.objects.filter(id=blocking_reason_id).first()
        if blocking_reason is None:
            return Response({"message": "Blocking reason not found"}, status=400)
        ticket.status = TicketStatus.HARD_BLOCKED
        ticket.decision_at = datetime.now()
        ticket.blocking_reason = blocking_reason
        ticket.moderator_comment = moderator_comment
        ticket.save()

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

        return Response({"message": "Product declined successfully"}, status=200)

    except Exception:
        return Response({"code": "SERVER_ERROR"}, status=500)
