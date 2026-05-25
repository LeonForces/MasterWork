from __future__ import annotations

import json
import logging
import threading
import time
from typing import Any

import requests
from pika.adapters.blocking_connection import BlockingChannel
from pika.spec import Basic, BasicProperties
from prometheus_client import start_http_server

from app.broker import Broker
from app.db import already_delivered, fetch_publish_candidates, log_delivery_attempt, mark_published, mark_retry
from app.metrics import DLQ_PUBLISH, OUTBOX_RETRIES, PUBLISH_ERROR, PUBLISH_SUCCESS, WEBHOOK_FAILURE, WEBHOOK_SUCCESS
from app.settings import settings

logger = logging.getLogger("integration-worker")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


def _connect_broker(stop_event: threading.Event) -> Broker | None:
    while not stop_event.is_set():
        try:
            return Broker()
        except Exception as exc:
            logger.warning("RabbitMQ connect failed: %s", exc)
            time.sleep(settings.poll_interval_seconds)
    return None


def publisher_loop(stop_event: threading.Event) -> None:
    broker: Broker | None = None
    try:
        while not stop_event.is_set():
            if broker is None:
                broker = _connect_broker(stop_event)
                if broker is None:
                    break

            candidates = fetch_publish_candidates(limit=100)
            if not candidates:
                time.sleep(settings.poll_interval_seconds)
                continue

            reconnect_required = False
            for row in candidates:
                outbox_id = row["outbox_id"]
                retry_count = int(row.get("retry_count", 0))
                payload = row["payload"]
                event_type = payload.get("event_type", "unknown")
                try:
                    broker.publish_event(payload, event_type)
                    mark_published(outbox_id)
                    PUBLISH_SUCCESS.inc()
                except Exception as exc:
                    retry_count += 1
                    terminal = retry_count >= settings.max_retry
                    mark_retry(outbox_id, retry_count, terminal=terminal)
                    PUBLISH_ERROR.inc()
                    if not terminal:
                        OUTBOX_RETRIES.inc()
                    logger.exception("Outbox publish failed outbox_id=%s retry=%s error=%s", outbox_id, retry_count, exc)
                    reconnect_required = True
                    break

            if reconnect_required and broker is not None:
                try:
                    broker.close()
                except Exception:
                    pass
                broker = None
                time.sleep(settings.poll_interval_seconds)
    finally:
        if broker is not None:
            broker.close()


def _deliver_webhook(payload: dict[str, Any]) -> tuple[bool, str | None]:
    try:
        response = requests.post(settings.webhook_target_url, json=payload, timeout=5)
        if 200 <= response.status_code < 300:
            return True, None
        return False, f"HTTP {response.status_code}"
    except Exception as exc:  # pragma: no cover
        return False, str(exc)


def consume_callback(
    broker: Broker,
    channel: BlockingChannel,
    method: Basic.Deliver,
    properties: BasicProperties,
    body: bytes,
) -> None:
    payload = json.loads(body.decode("utf-8"))
    event_id = payload.get("event_id", "")
    consumer_name = "webhook-default"

    headers = properties.headers or {}
    attempt = int(headers.get("delivery_attempt", 0))

    if event_id and already_delivered(event_id, consumer_name):
        channel.basic_ack(delivery_tag=method.delivery_tag)
        return

    success, error_text = _deliver_webhook(payload)
    if success:
        WEBHOOK_SUCCESS.inc()
        if event_id:
            log_delivery_attempt(event_id, consumer_name, "success", None)
        channel.basic_ack(delivery_tag=method.delivery_tag)
        return

    WEBHOOK_FAILURE.inc()
    if event_id:
        log_delivery_attempt(event_id, consumer_name, "failed", error_text)

    next_attempt = attempt + 1
    if next_attempt >= settings.max_retry:
        broker.publish_dlq(payload, reason=error_text or "max_retries")
        DLQ_PUBLISH.inc()
        channel.basic_ack(delivery_tag=method.delivery_tag)
        return

    # Requeue with attempt header and exponential delay.
    time.sleep(min(30, 2**next_attempt))
    broker.publish_event(
        payload,
        payload.get("event_type", "unknown"),
        headers={"delivery_attempt": next_attempt},
    )
    OUTBOX_RETRIES.inc()
    channel.basic_ack(delivery_tag=method.delivery_tag)


def _consume_with_broker(stop_event: threading.Event, broker: Broker) -> None:
    channel = broker.channel
    channel.basic_qos(prefetch_count=10)

    def _callback(ch: BlockingChannel, method: Basic.Deliver, props: BasicProperties, body: bytes) -> None:
        consume_callback(broker, ch, method, props, body)

    channel.basic_consume(queue=settings.rabbitmq_queue, on_message_callback=_callback, auto_ack=False)

    while not stop_event.is_set():
        broker.connection.process_data_events(time_limit=1)


def consumer_loop(stop_event: threading.Event) -> None:
    while not stop_event.is_set():
        broker = _connect_broker(stop_event)
        if broker is None:
            return
        try:
            _consume_with_broker(stop_event, broker)
        except Exception as exc:
            logger.warning("Consumer loop error, reconnecting: %s", exc)
            time.sleep(settings.poll_interval_seconds)
        finally:
            try:
                broker.close()
            except Exception:
                pass


def main() -> None:
    start_http_server(settings.metrics_port)
    logger.info("Integration metrics server started on :%s", settings.metrics_port)

    stop_event = threading.Event()

    publisher = threading.Thread(target=publisher_loop, args=(stop_event,), daemon=True)
    publisher.start()

    try:
        consumer_loop(stop_event)
    except KeyboardInterrupt:
        logger.info("Shutdown requested")
    finally:
        stop_event.set()
        publisher.join(timeout=5)


if __name__ == "__main__":
    main()
