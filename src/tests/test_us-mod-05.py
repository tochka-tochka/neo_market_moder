import time
import uuid

import pytest
from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from src.models.moderation import FieldReport, FieldReportSeverity, TicketStatus, Ticket
from src.tests.fixtures import (
    BaseTestUtil,
    moderation_worker,
    test_hard_block_reason,
    test_ticket,
)

from config.settings import MODER_SERVICE_KEY

@pytest.mark.django_db(transaction=True)
class TestSoftBlock(BaseTestUtil):
    def test_hard_block_transitions_to_terminal_and_emits_event(
        self, jwt_client, test_ticket, test_hard_block_reason
    ):
        url = reverse("block", args=[test_ticket.id])

        payload = {
            "blocking_reason_ids": [test_hard_block_reason.id],
            "comment": "comment",
            "field_reports": [
                {
                    "field_path": "skus[0].name",
                    "message": "message",
                    "severity": FieldReportSeverity.ERROR,
                }
            ],
        }

        response = jwt_client.post(url, data=payload, content_type="application/json")

        assert response.status_code == status.HTTP_200_OK, response.json()
        assert response.json()["status"] == TicketStatus.HARD_BLOCKED

        field_resports = FieldReport.objects.filter(ticket=test_ticket)
        assert len(field_resports) == len(payload["field_reports"])

    def test_hard_block_event_carries_hard_block_true(
        self, jwt_client, test_ticket, test_hard_block_reason
    ):
        self._clear_queues()
        url = reverse("block", args=[test_ticket.id])

        payload = {
            "blocking_reason_ids": [test_hard_block_reason.id],
            "comment": "comment",
            "field_reports": [
                {
                    "field_path": "status",
                    "message": "message",
                    "severity": FieldReportSeverity.ERROR,
                }
            ],
        }

        jwt_client.post(url, data=payload, content_type="application/json")

        msg = self.get_rabbitmq_message("moder_decisions")

        assert msg is not None
        assert msg["status"] == TicketStatus.BLOCKED
        assert msg["hard_block"]

    def test_any_modify_on_hard_blocked_returns_403(
        self, jwt_client, test_ticket, test_hard_block_reason
    ):
        url = reverse("block", args=[test_ticket.id])

        payload = {
            "blocking_reason_ids": [test_hard_block_reason.id],
            "comment": "comment",
            "field_reports": [
                {
                    "field_path": "skus[0].name",
                    "message": "message",
                    "severity": FieldReportSeverity.ERROR,
                }
            ],
        }

        response = jwt_client.post(url, data=payload, content_type="application/json")
        assert response.status_code == status.HTTP_200_OK, response.json()

        approve_url = reverse("approve", args=[test_ticket.id])

        response = jwt_client.post(approve_url)
        assert response.status_code == status.HTTP_403_FORBIDDEN, response.json()

        response = jwt_client.post(url, data=payload, content_type="application/json")
        assert response.status_code == status.HTTP_403_FORBIDDEN, response.json()

    def test_edited_event_on_hard_blocked_is_ignored(
        self,
        moderation_worker,
        jwt_client,
        test_ticket,
        test_hard_block_reason,
        test_user,
    ):
        url = reverse("block", args=[test_ticket.id])

        payload = {
            "blocking_reason_ids": [test_hard_block_reason.id],
            "comment": "comment",
            "field_reports": [
                {
                    "field_path": "skus[0].name",
                    "message": "message",
                    "severity": FieldReportSeverity.ERROR,
                }
            ],
        }

        response = jwt_client.post(url, data=payload, content_type="application/json")

        assert response.status_code == status.HTTP_200_OK, response.json()
        assert response.json()["status"] == TicketStatus.HARD_BLOCKED

        field_resports = FieldReport.objects.filter(ticket=test_ticket)
        assert len(field_resports) == len(payload["field_reports"])

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

        assert response.json()["status"] == TicketStatus.HARD_BLOCKED

    def test_deleted_event_removes_hard_blocked(
        self,
        moderation_worker,
        jwt_client,
        test_ticket,
        test_hard_block_reason,
        test_user,
    ):
        self._clear_queues()
        url = reverse("block", args=[test_ticket.id])

        payload = {
            "blocking_reason_ids": [test_hard_block_reason.id],
            "comment": "comment",
            "field_reports": [
                {
                    "field_path": "status",
                    "message": "message",
                    "severity": FieldReportSeverity.ERROR,
                }
            ],
        }

        response = jwt_client.post(url, data=payload, content_type="application/json")

        assert response.status_code == status.HTTP_200_OK, response.json()
        
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
