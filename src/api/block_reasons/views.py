from django.db.models import Q
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.parsers import JSONParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from src.models.moderation import BlockReason
from src.serializers import BlockReasonsSerializer


@api_view(["GET"])
@permission_classes([IsAuthenticated])
@parser_classes([JSONParser])
def get_block_reasons(request):
    try:
        query = Q(is_active=True)

        hard_block = request.query_params.get("hard_block")
        if hard_block is not None:
            if hard_block not in ["true", "false"]:
                return Response(
                    {
                        "code": "INVALID_PARAM",
                        "message": "invalid hard_block param value",
                    },
                    status=400,
                )
            query &= Q(hard_block=hard_block == "true")

        is_active = request.query_params.get("is_active")
        if is_active is not None:
            if is_active != "true":
                return Response(
                    {
                        "code": "INVALID_PARAM",
                        "message": "invalid is_active param value",
                    },
                    status=400,
                )
        else:
            query &= Q(is_active=True)

        reasons = BlockReason.objects.filter(query)
        serializer = BlockReasonsSerializer(reasons, many=True)
        return Response(serializer.data, status=200)
    except Exception:
        return Response({"code": "SERVER_ERROR"}, status=500)


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
@parser_classes([JSONParser])
def deactivate_block_reason(request, reason_id):
    try:
        reason = BlockReason.objects.filter(id=reason_id).first()
        if reason is None:
            return Response(
                {"code": "NOT_FOUND", "message": "blocking reason not found"},
                status=404,
            )

        related_tickets = reason.ticket_set.all()

        if len(related_tickets) > 0:
            return Response(
                {"code": "DEACTIVATE_CONFLICT", "message": "some tickets related to this reason"},
                status=409,
            )

        reason.is_active = False
        reason.save()
        return Response(status=204)
    except Exception:
        return Response({"code": "SERVER_ERROR"}, status=500)
