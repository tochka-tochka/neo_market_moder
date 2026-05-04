from rest_framework.decorators import api_view
from rest_framework.response import Response
from src.serializes import QueueSerializer
from src.models.moderation_queue import Queue
import src.schemas as schemas
from datetime import datetime

@api_view(['GET'])
def get_next_product(request):
    try:
        next_product = Queue.objects.all()[:1]

        #grpc client.getNextProduct()
        product = schemas.Product(
            id = "11111111-1111-1111-1111-111111111111",
            title="test",
            description="test",
            category=schemas.Category(
                id= "11111111-1111-1111-1111-111111111111",
                value="test"
            ),
            characteristics={
                "test": "test",
                "test": "test"
            },
            status=schemas.ProductStatus.ON_MODERATION,
            seller=schemas.Seller(
                username="test"
            ),
            images=[schemas.Image(
                id="test",
                url="test",
                order=0,
                created_at=datetime(2026, 1, 1)
            )],
            skus=[schemas.SKU(
                id="test",
                name="test",
                price=1,
                characteristics={
                    "test": "test",
                    "test": "test"
                },
                active_quantity=1
            )]
        )
        return Response(product)
    except Exception as e:
        return Response({"message": f"failed to get next product: {e}"}, status=500)