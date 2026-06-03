from rest_framework.parsers import JSONParser
from rest_framework.decorators import api_view, parser_classes
from rest_framework.response import Response

from src.models.moderation import Ticket
from src.serializers import TicketSerializer

class NotFoundException(Exception):
    pass

@api_view(["POST"])
def get_next_product(request):
    parser_classes = [JSONParser]
    try:
        if request.data["queue_priority"]:
            next = Ticket.objects.filter(queue_priority=request.data["queue_priority"])[:1][0] or None
        else:
            next = Ticket.objects.all()[:1][0] or None
            
        if next is None:
            return Response({"no products in queue"}, status=204)
        serializer = TicketSerializer(next)

        return Response(serializer.data)
    except Exception as e:
        return Response({"message": f"failed to get next product: {e}"}, status=500)
