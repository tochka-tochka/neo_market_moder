import json

import pika

class DecisionProd:
    def __init__(self):
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(host="localhost")
        )
        self.channel = connection.channel()

        self.channel.queue_declare(
            queue="moder_decisions", durable=True, arguments={"x-queue-type": "quorum"}
        )

    def send_decision(self, data):
        try:
            self.channel.basic_publish(
                exchange="", routing_key="moder_decisions", body=json.dumps(data)
            )
        except Exception as e:
            raise e

descision_queue = DecisionProd()