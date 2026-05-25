from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pytest  # noqa: E402

pytest.importorskip("pika")
pytest.importorskip("requests")

# Ensure we load integration-worker package, not API package with same "app" name.
for key in list(sys.modules.keys()):
    if key == "app" or key.startswith("app."):
        sys.modules.pop(key, None)

import app.main as integration_main  # noqa: E402


class BrokerStub:
    def __init__(self) -> None:
        self.published: list[tuple] = []
        self.dlq: list[tuple] = []

    def publish_event(self, payload, event_type, headers=None) -> None:  # noqa: ANN001
        self.published.append((payload, event_type, headers))

    def publish_dlq(self, payload, reason: str) -> None:  # noqa: ANN001
        self.dlq.append((payload, reason))


class ChannelStub:
    def __init__(self) -> None:
        self.acked: list[int] = []

    def basic_ack(self, delivery_tag: int) -> None:
        self.acked.append(delivery_tag)


class MethodStub:
    def __init__(self, tag: int) -> None:
        self.delivery_tag = tag


class PropertiesStub:
    def __init__(self, headers=None):  # noqa: ANN001
        self.headers = headers or {}


def test_consume_retry_republish(monkeypatch) -> None:
    broker = BrokerStub()
    channel = ChannelStub()
    method = MethodStub(tag=1)
    props = PropertiesStub(headers={"delivery_attempt": 0})
    body = b'{"event_id":"e1","event_type":"zone_enter"}'

    monkeypatch.setattr(integration_main, "_deliver_webhook", lambda payload: (False, "HTTP 500"))  # noqa: ARG005
    monkeypatch.setattr(integration_main, "already_delivered", lambda event_id, consumer: False)  # noqa: ARG005
    monkeypatch.setattr(integration_main, "log_delivery_attempt", lambda *args, **kwargs: None)
    monkeypatch.setattr(integration_main.time, "sleep", lambda _: None)
    monkeypatch.setattr(integration_main.settings, "max_retry", 3)

    integration_main.consume_callback(broker, channel, method, props, body)

    assert len(broker.published) == 1
    assert broker.published[0][2] == {"delivery_attempt": 1}
    assert channel.acked == [1]


def test_consume_retry_to_dlq(monkeypatch) -> None:
    broker = BrokerStub()
    channel = ChannelStub()
    method = MethodStub(tag=9)
    props = PropertiesStub(headers={"delivery_attempt": 2})
    body = b'{"event_id":"e2","event_type":"line_cross"}'

    monkeypatch.setattr(integration_main, "_deliver_webhook", lambda payload: (False, "HTTP 503"))  # noqa: ARG005
    monkeypatch.setattr(integration_main, "already_delivered", lambda event_id, consumer: False)  # noqa: ARG005
    monkeypatch.setattr(integration_main, "log_delivery_attempt", lambda *args, **kwargs: None)
    monkeypatch.setattr(integration_main.settings, "max_retry", 3)

    integration_main.consume_callback(broker, channel, method, props, body)

    assert len(broker.dlq) == 1
    assert broker.dlq[0][1] == "HTTP 503"
    assert channel.acked == [9]
