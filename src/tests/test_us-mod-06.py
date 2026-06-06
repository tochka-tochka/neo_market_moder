import pytest
from rest_framework import status
from rest_framework.reverse import reverse

from src.models.moderation import BlockReason
from src.tests.fixtures import test_ticket


@pytest.fixture
def test_block_reasons_list():
    reason1 = BlockReason.objects.create(
        code="TST-RSN-1",
        title="test",
        description="test",
        hard_block=False,
        is_active=True,
    )
    reason2 = BlockReason.objects.create(
        code="TST-RSN-2",
        title="test",
        description="test",
        hard_block=True,
        is_active=True,
    )
    reason3 = BlockReason.objects.create(
        code="TST-RSN-3",
        title="test",
        description="test",
        hard_block=False,
        is_active=True,
    )
    return reason1, reason2, reason3


@pytest.mark.django_db(transaction=True)
class TestBlockReasonsList:
    def test_list_returns_active_reasons(self, jwt_client, test_block_reasons_list):
        reason1, reason2, reason3 = test_block_reasons_list
        url = reverse("block-reasons")

        response = jwt_client.get(url)

        assert response.status_code == status.HTTP_200_OK

        ids = [reason["id"] for reason in response.json()]
        assert str(reason1.id) in ids
        assert str(reason2.id) in ids
        assert str(reason3.id) in ids

    def test_inactive_reasons_not_visible(self, jwt_client, test_block_reasons_list):
        reason1, reason2, reason3 = test_block_reasons_list
        reason4 = BlockReason.objects.create(
            code="TST-RSN-4",
            title="test",
            description="test",
            hard_block=False,
            is_active=False,
        )
        url = reverse("block-reasons")

        response = jwt_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()) == 3
        assert reason4 not in response.json()

    def test_referenced_reason_cannot_be_deleted(
        self, jwt_client, test_block_reasons_list, test_ticket
    ):
        reason1, reason2, reason3 = test_block_reasons_list
        test_ticket.blocking_reasons.add(reason1, reason2, reason3)

        url = reverse("deactivate-block-reason", args=[reason1.id])

        response = jwt_client.delete(url)

        assert response.status_code == status.HTTP_409_CONFLICT