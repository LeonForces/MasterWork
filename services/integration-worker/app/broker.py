from __future__ import annotations

import json
from typing import Any

import pika

from app.settings import settings


class Broker:
    def __init__(self) -> None:
        credentials = pika.PlainCredentials(settings.rabbitmq_user, settings.rabbitmq_password)
        params = pika.ConnectionParameters(
            host=settings.rabbitmq_host,
            port=settings.rabbitmq_port,
            credentials=credentials,
            heartbeat=30,
            blocked_connection_timeout=60,
        )
        self.connection = pika.BlockingConnection(params)
        self.channel = self.connection.channel()
        self.channel.confirm_delivery()
        self._declare_topology()

    def _declare_topology(self) -> None:
        self.channel.exchange_declare(exchange=settings.rabbitmq_exchange, exchange_type="topic", durable=True)

        self.channel.queue_declare(queue=settings.rabbitmq_dlq, durable=True)
        self.channel.queue_declare(queue=settings.rabbitmq_queue, durable=True)

        self.channel.queue_bind(queue=settings.rabbitmq_queue, exchange=settings.rabbitmq_exchange, routing_key="event.*.v1")
        self.channel.queue_bind(queue=settings.rabbitmq_dlq, exchange=settings.rabbitmq_exchange, routing_key="dlq.#")

    def publish_event(self, event_payload: dict[str, Any], event_type: str, headers: dict[str, Any] | None = None) -> None:
        routing_key = f"event.{event_type}.v1"
        body = json.dumps(event_payload).encode("utf-8")
        props = pika.BasicProperties(
            content_type="application/json",
            delivery_mode=2,
            headers=headers or {},
        )
        ok = self.channel.basic_publish(
            exchange=settings.rabbitmq_exchange,
            routing_key=routing_key,
            body=body,
            properties=props,
            mandatory=True,
        )
        # In publisher-confirm mode, Pika may signal publish errors via exceptions
        # (UnroutableError/NackError). Depending on Pika version and transport state,
        # basic_publish() can also return False even when message is accepted.
        # Treat False as failure only when channel/connection is already closed.
        if ok is False and (self.connection.is_closed or self.channel.is_closed):
            raise RuntimeError("RabbitMQ publish failed: channel/connection is closed")

    def publish_dlq(self, event_payload: dict[str, Any], reason: str) -> None:
        body = json.dumps(event_payload).encode("utf-8")
        props = pika.BasicProperties(
            content_type="application/json",
            delivery_mode=2,
            headers={"reason": reason},
        )
        ok = self.channel.basic_publish(
            exchange=settings.rabbitmq_exchange,
            routing_key=f"dlq.{event_payload.get('event_type', 'unknown')}.v1",
            body=body,
            properties=props,
            mandatory=True,
        )
        if ok is False and (self.connection.is_closed or self.channel.is_closed):
            raise RuntimeError("DLQ publish failed: channel/connection is closed")

    def close(self) -> None:
        try:
            self.channel.close()
        finally:
            self.connection.close()
