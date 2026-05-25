from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pytest  # noqa: E402

pytest.importorskip("pika")

from app.broker import Broker  # noqa: E402


class _FakeChannel:
    def __init__(self, publish_result: bool) -> None:
        self.publish_result = publish_result
        self.is_closed = False

    def basic_publish(self, **kwargs):  # noqa: ANN003
        return self.publish_result


class _FakeConn:
    def __init__(self, closed: bool = False) -> None:
        self.is_closed = closed


def _build_broker(publish_result: bool, conn_closed: bool = False, ch_closed: bool = False) -> Broker:
    broker = Broker.__new__(Broker)
    broker.connection = _FakeConn(closed=conn_closed)
    broker.channel = _FakeChannel(publish_result=publish_result)
    broker.channel.is_closed = ch_closed
    return broker


def test_publish_event_does_not_fail_on_false_with_open_channel() -> None:
    broker = _build_broker(publish_result=False, conn_closed=False, ch_closed=False)
    broker.publish_event({"event_id": "e1"}, "zone_enter")


def test_publish_event_fails_on_false_when_channel_closed() -> None:
    broker = _build_broker(publish_result=False, conn_closed=False, ch_closed=True)
    with pytest.raises(RuntimeError):
        broker.publish_event({"event_id": "e2"}, "zone_enter")


def test_publish_dlq_does_not_fail_on_false_with_open_channel() -> None:
    broker = _build_broker(publish_result=False, conn_closed=False, ch_closed=False)
    broker.publish_dlq({"event_id": "e3", "event_type": "zone_enter"}, reason="test")
