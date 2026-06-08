import queue
import threading
import uuid
from datetime import datetime, timedelta

import pytest
from django import db
from django.contrib.auth.models import User
from django.test import TransactionTestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from src.models.moderation import Ticket, TicketKind, TicketStatus
from src.tests.fixtures import test_soft_block_reason


@pytest.fixture
def test_tickets_queue(request, test_user):
    statuses = getattr(
        request,
        "param",
        [TicketStatus.PENDING, TicketStatus.PENDING, TicketStatus.PENDING],
    )

    ticket1 = Ticket.objects.create(
        product_id=uuid.uuid4(),
        seller_id=uuid.uuid4(),
        kind=TicketKind.CREATE,
        status=statuses[0],
        queue_priority=2,
        json_after={
            "price": 100,
            "status": "new",
            "skus": [{"name": "sku_1"}, {"name": "sku_1"}],
        },
        created_at=datetime(2026, 6, 1, 15, 30, 0),
        updated_at=datetime(2026, 6, 1, 15, 30, 0),
        assigned_moderator=None,
    )

    ticket2 = Ticket.objects.create(
        product_id=uuid.uuid4(),
        seller_id=uuid.uuid4(),
        kind=TicketKind.EDIT,
        status=statuses[1],
        queue_priority=1,
        json_after={
            "price": 100,
            "status": "new",
            "skus": [{"name": "sku_1"}, {"name": "sku_1"}],
        },
        created_at=datetime(2026, 6, 1, 15, 30, 0),
        updated_at=datetime(2026, 6, 2, 15, 30, 0),
        assigned_moderator=None,
    )

    ticket3 = Ticket.objects.create(
        product_id=uuid.uuid4(),
        seller_id=uuid.uuid4(),
        kind=TicketKind.EDIT,
        status=statuses[2],
        queue_priority=1,
        json_after={
            "price": 100,
            "status": "new",
            "skus": [{"name": "sku_1"}, {"name": "sku_1"}],
        },
        created_at=datetime(2026, 6, 1, 15, 30, 0),
        updated_at=datetime(2026, 6, 3, 15, 30, 0),
        assigned_moderator=None,
    )
    return ticket1, ticket2, ticket3


@pytest.mark.django_db(transaction=True)
class TestGettingNextTicket:
    def test_next_returns_oldest_pending(self, jwt_client, test_tickets_queue):
        ticket1, ticket2, ticket3 = test_tickets_queue
        url = reverse("get-next")

        response = jwt_client.post(url)

        assert response.status_code == status.HTTP_200_OK, response.json()
        assert response.json()["status"] == TicketStatus.IN_REVIEW
        assert response.json()["id"] == str(ticket2.id)

    def test_concurrent_two_moderators_get_different_cards(self, test_tickets_queue):
        url = reverse("get-next")

        user1 = User.objects.create_user(username="moderator1", password="password123")
        client1 = APIClient()
        client1.credentials(
            HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user1).access_token}"
        )

        user2 = User.objects.create_user(username="moderator2", password="password123")
        client2 = APIClient()
        client2.credentials(
            HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user2).access_token}"
        )

        q = queue.Queue()

        barrier = threading.Barrier(2)

        def make_request(client, queue_to_put):
            try:
                barrier.wait()
                response = client.post(url)
                queue_to_put.put(response)
                db.close_old_connections()
            except Exception as e:
                queue_to_put.put(e)

        thread1 = threading.Thread(target=make_request, args=(client1, q))
        thread2 = threading.Thread(target=make_request, args=(client2, q))

        thread1.start()
        thread2.start()

        thread1.join()
        thread2.join()

        res1 = q.get()
        res2 = q.get()

        assert not isinstance(res1, Exception), f"{res1}"
        assert not isinstance(res2, Exception), f"{res2}"

        assert res1.status_code == status.HTTP_200_OK, res1.json()
        assert res2.status_code == status.HTTP_200_OK, res2.json()

        assert res1.json()["id"] != res2.json()["id"]

    def test_empty_queue_returns_204(self, jwt_client):
        url = reverse("get-next")

        response = jwt_client.post(url)

        assert response.status_code == status.HTTP_204_NO_CONTENT, response.json()

    def test_moderator_already_has_in_review_returns_409(
        self, jwt_client, test_tickets_queue
    ):
        url = reverse("get-next")

        jwt_client.post(url)

        response = jwt_client.post(url)

        assert response.status_code == status.HTTP_409_CONFLICT, response.json()
