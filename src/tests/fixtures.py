import json
from datetime import datetime, timedelta
from django.utils import timezone
import pika
import pytest
import threading
import time

from src.models.moderation import BlockReason, Ticket, TicketKind, TicketStatus


@pytest.fixture
def test_soft_block_reason():
    reason = BlockReason.objects.create(
        code="TST-RSN",
        title="test",
        description="test",
        hard_block=False,
        is_active=True,
    )
    return reason

@pytest.fixture
def test_hard_block_reason():
    reason = BlockReason.objects.create(
        code="TST-RSN-HRD",
        title="test",
        description="test",
        hard_block=True,
        is_active=True,
    )
    return reason


@pytest.fixture
def test_ticket(request, test_user):

    status = getattr(request, "param", TicketStatus.IN_REVIEW)

    ticket = Ticket.objects.create(
        product_id="8851365d-0285-46e8-b7a4-8cbf63b04baa",
        seller_id="b4405305-aae4-4c39-b175-fd5a7638e7ba",
        kind=TicketKind.CREATE,
        status=status,
        queue_priority=1,
        json_after={
            "price": 100,
            "status": "new",
            "skus": [{"name": "sku_1"}, {"name": "sku_1"}],
        },
        created_at=timezone.now(),
        updated_at=timezone.now(),
        claimed_at=timezone.now(),
        claim_expires_at=timezone.make_aware(datetime.now() + timedelta(minutes=30)),
        assigned_moderator=test_user,
    )
    return ticket

@pytest.fixture
def moderation_worker():
    from interservice_queues.consumer.consumer import (
        ProductEventsConsumer,
    )

    consumer_instance = ProductEventsConsumer()
    consumer_thread = threading.Thread(
        target=consumer_instance.channel.start_consuming, daemon=True
    )
    consumer_thread.start()
    time.sleep(1)

    yield consumer_thread

    if consumer_instance.channel.is_open:
        consumer_instance.channel.stop_consuming()
    consumer_thread.join(timeout=1)


class BaseTestUtil:
    def get_rabbitmq_message(self, queue_name, timeout=5):
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(host="localhost", port=5672)
        )
        channel = connection.channel()
        channel.queue_declare(
            queue=queue_name, durable=True, arguments={"x-queue-type": "quorum"}
        )

        received_body = None

        def callback(ch, method, properties, body):
            nonlocal received_body
            received_body = json.loads(body.decode())
            ch.stop_consuming()

        channel.basic_consume(
            queue=queue_name, on_message_callback=callback, auto_ack=True
        )
        try:
            connection.process_data_events(time_limit=timeout)
        finally:
            connection.close()
        return received_body

    def send_b2b_events(self, data: dict):
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(host="localhost", port=5672)
        )
        try:
            channel = connection.channel()

            channel.queue_declare(
                queue="moder",
                durable=True,
                arguments={"x-queue-type": "quorum"},
            )

            channel.basic_publish(
                exchange="", routing_key="moder", body=json.dumps(data)
            )
        finally:
            connection.close()

    def _clear_queues(self):
        self.get_rabbitmq_message("moder", timeout=0.1)
        self.get_rabbitmq_message("b2c", timeout=0.1)
        self.get_rabbitmq_message("moder_decisions", timeout=0.1)
