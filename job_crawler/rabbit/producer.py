
import json
import os

import pika
from dotenv import load_dotenv


load_dotenv()


RABBITMQ_URL = os.getenv("RABBITMQ_URL")
RABBITMQ_QUEUE = os.getenv(
    "RABBITMQ_QUEUE",
    "crawl_queue"
)


def get_connection():

    if not RABBITMQ_URL:
        raise ValueError(
            "RABBITMQ_URL is not configured"
        )

    parameters = pika.URLParameters(
        RABBITMQ_URL
    )

    return pika.BlockingConnection(
        parameters
    )


def publish_crawl_job(
    request_id: str,
    crawler: str = "itviec"
):

    message = {
        "request_id": request_id,
        "crawler": crawler
    }

    connection = get_connection()

    try:

        channel = connection.channel()

        # ----------------------------------------------------
        # Tạo queue nếu chưa tồn tại
        # ----------------------------------------------------

        channel.queue_declare(
            queue=RABBITMQ_QUEUE,
            durable=True
        )

        # ----------------------------------------------------
        # Gửi message
        # ----------------------------------------------------

        channel.basic_publish(
            exchange="",
            routing_key=RABBITMQ_QUEUE,
            body=json.dumps(message),
            properties=pika.BasicProperties(
                delivery_mode=2,
                content_type="application/json"
            )
        )

        print(
            f"Published crawl job: {request_id}"
        )

    finally:

        connection.close()
