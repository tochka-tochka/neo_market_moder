import time
import uuid
from datetime import datetime, timedelta

import pytest
from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework import status
from rest_framework.reverse import reverse

from config.settings import MODER_SERVICE_KEY
from src.models.moderation import Ticket, TicketKind, TicketStatus
from src.serializers import TicketSerializer
from src.tests.fixtures import (
    BaseTestUtil,
    moderation_worker,
    test_soft_block_reason,
    test_ticket,
)


@pytest.mark.django_db(transaction=True)
class TestEventConsume(BaseTestUtil):
    def test_created_pending(self, moderation_worker, test_user):
        product_id = str(uuid.uuid4())
        self.send_b2b_events(
            data={
                "X-Service-Key": MODER_SERVICE_KEY,
                "idempotency_key": str(uuid.uuid4()),
                "event_type": "CREATED",
                "ocuured_at": str(timezone.now()),
                "payload": {
                    "product_id": product_id,
                    "product": {
                        "id": product_id,
                        "seller_id": test_user.id,
                        "skus": [{"active_quantity": 5}],
                        "test_product_info": "test_product_info",
                    },
                },
            }
        )
        time.sleep(0.5)

        ticket = Ticket.objects.filter(product_id=product_id).first()
        assert ticket is not None
        assert ticket.status == TicketStatus.PENDING

    @pytest.mark.parametrize("test_ticket", [TicketStatus.MODERATED], indirect=True)
    def test_edited_returns_moderated_to_review(
        self, moderation_worker, test_ticket, test_user
    ):
        self.send_b2b_events(
            data={
                "X-Service-Key": MODER_SERVICE_KEY,
                "idempotency_key": str(uuid.uuid4()),
                "event_type": "EDITED",
                "ocuured_at": str(timezone.now()),
                "payload": {
                    "product_id": test_ticket.product_id,
                    "product": {
                        "id": test_ticket.product_id,
                        "seller_id": test_user.id,
                        "skus": [{"active_quantity": 5}],
                        "test_product_info": "test_product_info",
                    },
                },
            }
        )
        time.sleep(0.5)

        ticket = Ticket.objects.filter(product_id=test_ticket.product_id).first()
        assert ticket is not None
        assert ticket.status == TicketStatus.PENDING

    @pytest.mark.parametrize("test_ticket", [TicketStatus.BLOCKED], indirect=True)
    def test_edited_returns_blocked_to_review(
        self, moderation_worker, test_ticket, test_user
    ):
        self.send_b2b_events(
            data={
                "X-Service-Key": MODER_SERVICE_KEY,
                "idempotency_key": str(uuid.uuid4()),
                "event_type": "EDITED",
                "ocuured_at": str(timezone.now()),
                "payload": {
                    "product_id": test_ticket.product_id,
                    "product": {
                        "id": test_ticket.product_id,
                        "seller_id": test_user.id,
                        "skus": [{"active_quantity": 5}],
                        "test_product_info": "test_product_info",
                    },
                },
            }
        )
        time.sleep(0.5)

        ticket = Ticket.objects.filter(product_id=test_ticket.product_id).first()
        assert ticket is not None
        assert ticket.status == TicketStatus.PENDING

    @pytest.mark.parametrize("test_ticket", [TicketStatus.IN_REVIEW], indirect=True)
    def test_edited_updates_in_review(self, moderation_worker, test_ticket, test_user):
        self.send_b2b_events(
            data={
                "X-Service-Key": MODER_SERVICE_KEY,
                "idempotency_key": str(uuid.uuid4()),
                "event_type": "EDITED",
                "ocuured_at": str(timezone.now()),
                "payload": {
                    "product_id": test_ticket.product_id,
                    "product": {
                        "id": test_ticket.product_id,
                        "seller_id": test_user.id,
                        "skus": [{"active_quantity": 5}],
                        "test_product_info": "test_product_info",
                    },
                },
            }
        )
        time.sleep(0.5)

        ticket = Ticket.objects.filter(product_id=test_ticket.product_id).first()
        assert ticket is not None
        assert ticket.status == TicketStatus.PENDING
        assert ticket.json_after["test_product_info"] == "test_product_info"

    def test_deleted_archived(self, moderation_worker, test_ticket, test_user):
        self.send_b2b_events(
            data={
                "X-Service-Key": MODER_SERVICE_KEY,
                "idempotency_key": str(uuid.uuid4()),
                "event_type": "DELETED",
                "ocuured_at": str(timezone.now()),
                "payload": {
                    "product_id": test_ticket.product_id,
                },
            }
        )
        time.sleep(0.5)

        ticket = Ticket.objects.filter(product_id=test_ticket.product_id).first()
        assert ticket is None

    def test_duplicate_event_no_side_effects(self, moderation_worker, test_user):
        idempotency_key = str(uuid.uuid4())
        self.send_b2b_events(
            data={
                "X-Service-Key": MODER_SERVICE_KEY,
                "idempotency_key": idempotency_key,
                "event_type": "CREATED",
                "ocuured_at": str(timezone.now()),
                "payload": {
                    "product_id": str(uuid.uuid4()),
                    "product": {
                        "id": str(uuid.uuid4()),
                        "seller_id": test_user.id,
                        "skus": [{"active_quantity": 5}],
                        "test_product_info": "test_product_info",
                    },
                },
            }
        )
        time.sleep(0.5)

        self.send_b2b_events(
            data={
                "X-Service-Key": MODER_SERVICE_KEY,
                "idempotency_key": idempotency_key,
                "event_type": "CREATED",
                "ocuured_at": str(timezone.now()),
                "payload": {
                    "product_id": str(uuid.uuid4()),
                    "product": {
                        "id": str(uuid.uuid4()),
                        "seller_id": test_user.id,
                        "skus": [{"active_quantity": 5}],
                        "test_product_info": "test_product_info",
                    },
                },
            }
        )
        time.sleep(0.5)

        tickets_count = Ticket.objects.all().count()
        assert tickets_count == 1

    def test_missing_service_header_request_rejected(self, moderation_worker, test_user):
        product_id = str(uuid.uuid4())
        self.send_b2b_events(
            data={
                "idempotency_key": str(uuid.uuid4()),
                "event_type": "CREATED",
                "ocuured_at": str(timezone.now()),
                "payload": {
                    "product_id": product_id,
                    "product": {
                        "id": product_id,
                        "seller_id": test_user.id,
                        "skus": [{"active_quantity": 5}],
                        "test_product_info": "test_product_info",
                    },
                },
            }
        )
        time.sleep(0.5)

        ticket = Ticket.objects.filter(product_id=product_id).first()
        assert ticket is None
