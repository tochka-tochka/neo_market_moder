from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import JSONParser
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.response import Response
from src.models.moderation import BlockReason
from src.serializers import BlockReasonsSerializer

@api_view(['GET'])
@permission_classes([IsAuthenticated])
@parser_classes([JSONParser])
def get_block_reasons(request):
    try:
        reasons = BlockReason.objects.all()
        serializer = BlockReasonsSerializer(reasons, many=True)
        return Response(serializer.data)
    except Exception as e:
        return Response({"message": f"failed get block reasons: {e}"}, status=500)