import json
import os

from src.serializers import TicketSerializer, TicketSummarySerializer

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django

django.setup()

from src.models.moderation import Ticket, TicketKind, TicketStatus

MODER_SERVICE_KEY = os.environ.get("MODER_SERVICE_KEY")


class ProductHardBlocked(Exception):
    pass


class RepeatedCreateRequest(Exception):
    pass


class ProductNotFound(Exception):
    pass


def process_created_event(data):
    try:
        prev_product_state = Ticket.objects.filter(
            product_id=data["product_id"]
        ).first()
        if prev_product_state is not None:
            if prev_product_state.status == TicketStatus.HARD_BLOCKED:
                raise ProductHardBlocked
            raise RepeatedCreateRequest
        Ticket.objects.create(
            product_id=data["product_id"],
            seller_id=data["product"]["seller_id"],
            json_after=data["product"],
            kind=TicketKind.CREATE,
            status=TicketStatus.PENDING,
        )
    except ProductHardBlocked:
        return Exception("product is hard-blocked")
    except RepeatedCreateRequest:
        return Exception("product already created")
    except Exception as e:
        return Exception(f"failed to proccess product event: {e}")


def process_edited_event(data):
    try:
        prev_product_state = Ticket.objects.filter(
            product_id=data["product_id"]
        ).first()

        if prev_product_state is None:
            raise ProductNotFound

        if prev_product_state.status == TicketStatus.HARD_BLOCKED:
            raise ProductHardBlocked

        prev_product_state.json_before = prev_product_state.json_after
        prev_product_state.json_after = data["product"]

        active_quantity = sum(
            list(map(lambda sku: sku["active_quantity"], data["product"]["skus"]))
        )
        if prev_product_state.status == TicketStatus.BLOCKED:
            prev_product_state.queue_priority = 2
        elif active_quantity > 0:
            prev_product_state.queue_priority = 3
        elif active_quantity == 0:
            prev_product_state.queue_priority = 4

        prev_product_state.status = TicketStatus.PENDING
        prev_product_state.assigned_moderator = None
        prev_product_state.save()
    except ProductHardBlocked:
        return Exception("product is hard-blocked")
    except RepeatedCreateRequest:
        return Exception("product already created")
    except Exception as e:
        return Exception(f"failed to proccess product event: {e}")


def process_deleted_event(data):
    try:
        prev_product_state = Ticket.objects.filter(product_id=data["product_id"]).first()

        if prev_product_state is None:
            return

        prev_product_state.delete()

    except Exception as e:
        return Exception(f"failed to proccess product event: {e}")
