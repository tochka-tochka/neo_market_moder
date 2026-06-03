from rest_framework.decorators import api_view
from rest_framework.response import Response
from src.models.moderation import BlockReason
from src.serializers import BlockReasonsSerializer

@api_view(['GET'])
def get_block_reasons(request):
    try:
        reasons = BlockReason.objects.all()
        serializer = BlockReasonsSerializer(reasons, many=True)
        return Response(serializer.data)
    except Exception as e:
        return Response({"message": f"failed get block reasons: {e}"}, status=500)