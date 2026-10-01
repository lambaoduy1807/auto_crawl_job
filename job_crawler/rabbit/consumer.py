import json
import os
from datetime import datetime

import pika
from dotenv import load_dotenv

from job_crawler.redis_client import redis_client


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


def update_status(
    request_id: str,
    status: str,
    **kwargs
):
    """
    Cập nhật trạng thái request trong Redis.
    """

    data = {
        "status": status,
        **kwargs
    }

    redis_client.hset(
        f"crawl:{request_id}",
        mapping=data
    )

    print(
        f"[Redis] Request {request_id} "
        f"-> {status}"
    )


def run_crawl4ai():
    """Run all Crawl4AI sources and return the combined jobs."""
    from job_crawler.craw4ai.run_all import run_all_crawlers

    return run_all_crawlers()


def callback(
    ch,
    method,
    properties,
    body
):

    request_id = None

    try:

        # ====================================================
        # 1. Đọc message từ RabbitMQ
        # ====================================================

        message = json.loads(body)

        request_id = message["request_id"]

        crawler = message.get("crawler", "all-crawl4ai")

        print("=" * 60)

        print("Received crawl job")

        print(
            f"Request ID : {request_id}"
        )

        print(
            f"Crawler    : {crawler}"
        )

        print(
            f"Redelivered: {method.redelivered}"
        )

        print("=" * 60)


        # ====================================================
        # 2. Cập nhật status -> running
        # ====================================================

        update_status(
            request_id=request_id,
            status="running",
            started_at=datetime.now().isoformat(),
            error=""
        )


        # ====================================================
        # 3. Chạy toàn bộ crawler Crawl4AI
        # ====================================================

        jobs = run_crawl4ai()


        # ====================================================
        # 4. Lưu kết quả hợp nhất vào Redis
        # ====================================================

        redis_client.hset(
            f"crawl:{request_id}",
            mapping={"result": json.dumps(jobs, ensure_ascii=False)}
        )


        # ====================================================
        # 5. Cập nhật status -> completed
        # ====================================================

        update_status(
            request_id=request_id,
            status="completed",
            completed_at=datetime.now().isoformat()
        )


        # ====================================================
        # 6. ACK RabbitMQ
        # ====================================================

        ch.basic_ack(
            delivery_tag=method.delivery_tag
        )

        print(
            f"Job completed: {request_id}"
        )


    except Exception as e:

        print("=" * 60)

        print(
            f"Job failed: {request_id}"
        )

        print(
            f"Error: {e}"
        )

        print("=" * 60)


        # ====================================================
        # 7. Cập nhật status -> failed
        # ====================================================

        if request_id:

            update_status(
                request_id=request_id,
                status="failed",
                completed_at=datetime.now().isoformat(),
                error=str(e)
            )


        # ====================================================
        # 8. Đưa message trở lại RabbitMQ
        # ====================================================

        ch.basic_nack(
            delivery_tag=method.delivery_tag,
            requeue=False
        )


def start_consumer():

    connection = get_connection()

    channel = connection.channel()

    channel.queue_declare(
        queue=RABBITMQ_QUEUE,
        durable=True
    )

    # Chỉ nhận 1 job tại một thời điểm
    channel.basic_qos(
        prefetch_count=1
    )

    channel.basic_consume(
        queue=RABBITMQ_QUEUE,
        on_message_callback=callback,
        auto_ack=False
    )

    print("=" * 60)

    print(
        "RabbitMQ Consumer started"
    )

    print(
        f"Queue: {RABBITMQ_QUEUE}"
    )

    print(
        "Waiting for crawl jobs..."
    )

    print("=" * 60)

    try:

        channel.start_consuming()

    except KeyboardInterrupt:

        print(
            "Stopping consumer..."
        )

        channel.stop_consuming()

    finally:

        connection.close()


if __name__ == "__main__":

    start_consumer()
