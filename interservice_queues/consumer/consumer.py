import json
import os

import pika
from django import db
from interservice_queues.consumer.service.main import (
    process_created_event,
    process_deleted_event,
    process_edited_event,
)

from config.settings import MODER_SERVICE_KEY

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django

django.setup()

from src.models.moderation import EventsIdempotencyKeys


class ProductEventsConsumer:
    def __init__(self):
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(host="localhost", port=5672)
        )
        self.channel = connection.channel()

        self.channel.queue_declare(
            queue="moder", durable=True, arguments={"x-queue-type": "quorum"}
        )

        self.channel.basic_consume(
            queue="moder", on_message_callback=self.process_product_event, auto_ack=True
        )

    def process_product_event(self, channel, method, props, body):
        data = json.loads(body)
        if data["X-Service-Key"] != MODER_SERVICE_KEY:
            return Exception("Access Denied")

        if EventsIdempotencyKeys.objects.filter(idempotency_key=data["idempotency_key"]).first() is not None:
            return

        match data["event_type"]:
            case "CREATED":
                process_created_event(data["payload"])
            case "EDITED":
                process_edited_event(data["payload"])
            case "DELETED":
                process_deleted_event(data["payload"])

        EventsIdempotencyKeys.objects.create(idempotency_key=data["idempotency_key"])
        
        db.close_old_connections()
