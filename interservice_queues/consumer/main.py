import threading
from .consumer import product_events

if __name__ == "__main__":
    consumer_threading = threading.Thread(target=product_events.channel.start_consuming, daemon=True)
    consumer_threading.start()