import uuid
import threading
import time
from datetime import datetime, timedelta

import pytest
from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework import status
from rest_framework.reverse import reverse

from config.settings import MODER_SERVICE_KEY
from src.models.moderation import Ticket, TicketKind, TicketStatus
from src.tests.fixtures import BaseTestUtil, test_soft_block_reason, test_ticket, moderation_worker


@pytest.mark.django_db(transaction=True)
class TestTicketApprove(BaseTestUtil):
    def test_approve_transitions_to_moderated_and_emits_event(
        self, jwt_client, test_ticket
    ):
        url = reverse("approve", args=[test_ticket.id])

        response = jwt_client.post(url, json={"comment": "test_comment"})

        assert response.status_code == status.HTTP_200_OK, response.json()
        assert response.json()["product_id"] == test_ticket.product_id
        assert response.json()["status"] == TicketStatus.MODERATED

        msg = self.get_rabbitmq_message("moder_decisions")

        assert msg is not None
        assert msg["product_id"] == test_ticket.product_id

    def test_approve_others_card_returns_403(self, jwt_client):
        another_user = User.objects.create(username="testrfdst", password="34rewtg")
        ticket = Ticket.objects.create(
            product_id="8851365d-0285-46e8-b7a4-8cbf63b04baa",
            seller_id="b4405305-aae4-4c39-b175-fd5a7638e7ba",
            kind=TicketKind.CREATE,
            status=TicketStatus.IN_REVIEW,
            queue_priority=1,
            json_after={
                "price": 100,
                "status": "new",
                "skus": [{"name": "sku_1"}, {"name": "sku_1"}],
            },
            created_at=timezone.now(),
            updated_at=timezone.now(),
            claimed_at=timezone.now(),
            claim_expires_at=timezone.now() + timedelta(minutes=30),
            assigned_moderator=another_user,
        )
        url = reverse("approve", args=[ticket.id])

        response = jwt_client.post(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN, response.json()

        _ = self.get_rabbitmq_message("moder_decisions")

    def test_approve_without_sku_returns_409(self, jwt_client, test_user):
        ticket = Ticket.objects.create(
            product_id="8851365d-0285-46e8-b7a4-8cbf63b04baa",
            seller_id="b4405305-aae4-4c39-b175-fd5a7638e7ba",
            kind=TicketKind.CREATE,
            status=TicketStatus.IN_REVIEW,
            queue_priority=1,
            json_after={
                "price": 100,
                "status": "new",
                "skus": [],
            },
            created_at=timezone.now(),
            updated_at=timezone.now(),
            claimed_at=timezone.now(),
            claim_expires_at=timezone.now() + timedelta(minutes=30),
            assigned_moderator=test_user,
        )
        url = reverse("approve", args=[ticket.id])

        response = jwt_client.post(url)

        assert response.status_code == status.HTTP_409_CONFLICT, response.json()

        _ = self.get_rabbitmq_message("moder_decisions")

    def test_approve_after_edited_returns_409(
        self, jwt_client, test_ticket, moderation_worker
    ):
        url = reverse("approve", args=[test_ticket.id])

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
                        "skus": [{"active_quantity": 5}],
                    },
                },
            }
        )

        time.sleep(1)

        response = jwt_client.post(url)
        assert response.status_code == status.HTTP_409_CONFLICT, response.json()
