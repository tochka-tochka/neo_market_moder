import json
import os

import pika

from interservice_queues.consumer.service.main import (
    process_created_event,
    process_deleted_event,
    process_edited_event,
)

MODER_SERVICE_KEY = os.environ.get("MODER_SERVICE_KEY")


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
            queue="moder", on_message_callback=self.process_product_event
        )

    def process_product_event(channel, method, props, body):
        data = json.loads(body)
        if data["X-Service-Key"] != MODER_SERVICE_KEY:
            return Exception("Access Denied")

        match data["event_type"]:
            case "CREATED":
                process_created_event(data["payload"])
            case "EDITED":
                process_edited_event(data["payload"])
            case "DELETED":
                process_deleted_event(data["payload"])

product_events = ProductEventsConsumer()
