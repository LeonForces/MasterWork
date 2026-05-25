from __future__ import annotations

from prometheus_client import Counter

PUBLISH_SUCCESS = Counter("integration_outbox_publish_success_total", "Outbox publish success")
PUBLISH_ERROR = Counter("integration_outbox_publish_error_total", "Outbox publish errors")
OUTBOX_RETRIES = Counter("integration_outbox_retry_total", "Outbox retries")
WEBHOOK_SUCCESS = Counter("integration_webhook_success_total", "Webhook delivery success")
WEBHOOK_FAILURE = Counter("integration_webhook_failure_total", "Webhook delivery failure")
DLQ_PUBLISH = Counter("integration_dlq_publish_total", "Messages sent to DLQ")
