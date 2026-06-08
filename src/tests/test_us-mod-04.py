import pytest
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from src.models.moderation import FieldReport, FieldReportSeverity, TicketStatus
from src.tests.fixtures import BaseTestUtil, test_soft_block_reason, test_ticket


@pytest.mark.django_db
class TestSoftBlock(BaseTestUtil):
    def test_soft_block_transitions_to_blocked_with_field_reports(
        self, jwt_client, test_ticket, test_soft_block_reason
    ):
        url = reverse("block", args=[test_ticket.id])

        payload = {
            "blocking_reason_ids": [test_soft_block_reason.id],
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
        assert response.json()["status"] == TicketStatus.BLOCKED

        field_resports = FieldReport.objects.filter(ticket=test_ticket)
        assert len(field_resports) == len(payload["field_reports"])

    def test_soft_block_emits_event_to_b2b(
        self, jwt_client, test_ticket, test_soft_block_reason
    ):
        self._clear_queues()
        url = reverse("block", args=[test_ticket.id])

        payload = {
            "blocking_reason_ids": [test_soft_block_reason.id],
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
        assert not msg["hard_block"]

    def test_soft_block_unknown_reason_returns_400(
        self, jwt_client, test_ticket, test_soft_block_reason
    ):
        url = reverse("block", args=[test_ticket.id])

        payload = {
            "blocking_reason_ids": ["00000000-0000-0000-0000-000000000000"],
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

        assert response.status_code == status.HTTP_400_BAD_REQUEST, response.json()

    def test_soft_block_others_card_returns_403(
        self, jwt_client, test_ticket, test_soft_block_reason
    ):
        url = reverse("block", args=[test_ticket.id])

        payload = {
            "blocking_reason_ids": ["00000000-0000-0000-0000-000000000000"],
            "comment": "comment",
            "field_reports": [
                {
                    "field_path": "status",
                    "message": "message",
                    "severity": FieldReportSeverity.ERROR,
                }
            ],
        }

        another_user = User.objects.create_user(
            username="moderator1", password="password123"
        )
        another_client = APIClient()
        another_client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(another_user).access_token}"
        )

        response = another_client.post(url, data=payload, content_type="application/json")

        assert response.status_code == status.HTTP_403_FORBIDDEN, response.json()

    def test_soft_block_invalid_field_name_returns_400(
        self, jwt_client, test_ticket, test_soft_block_reason
    ):
        url = reverse("block", args=[test_ticket.id])

        payload = {
            "blocking_reason_ids": ["00000000-0000-0000-0000-000000000000"],
            "comment": "comment",
            "field_reports": [
                {
                    "field_path": "fdfsahds",
                    "message": "message",
                    "severity": FieldReportSeverity.ERROR,
                }
            ],
        }

        response = jwt_client.post(url, data=payload, content_type="application/json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST, response.json()
