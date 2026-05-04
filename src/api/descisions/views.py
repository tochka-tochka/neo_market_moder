from rest_framework.response import Response
from rest_framework.decorators import api_view

@api_view(['POST'])
def accept(request, product_id):
    try:
        #grpc client.Accept(product_id)
        return Response(product_id)
    except Exception as e:
        return Response({"message": f"failed to accept product {e}"}, status=500)

@api_view(['POST'])
def decline(request, product_id):
    try:
        #grpc client.Decline(product_id)
        return Response(product_id)
    except Exception as e:
        return Response({"message": f"failed to decline product {e}"}, status=500)