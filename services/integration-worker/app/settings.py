from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = Field(
        default="postgresql+psycopg2://video_app:video_app_password@postgres:5432/video_analytics",
        alias="DATABASE_URL",
    )

    rabbitmq_user: str = Field(default="video_app", alias="RABBITMQ_USER")
    rabbitmq_password: str = Field(default="video_app_password", alias="RABBITMQ_PASSWORD")
    rabbitmq_host: str = Field(default="rabbitmq", alias="RABBITMQ_HOST")
    rabbitmq_port: int = Field(default=5672, alias="RABBITMQ_PORT")
    rabbitmq_exchange: str = Field(default="events.topic.v1", alias="RABBITMQ_EXCHANGE")
    rabbitmq_queue: str = Field(default="integration.webhook.v1", alias="RABBITMQ_QUEUE")
    rabbitmq_dlq: str = Field(default="integration.webhook.v1.dlq", alias="RABBITMQ_DLQ")

    webhook_target_url: str = Field(default="http://webhook-mock:8090/webhook/events", alias="WEBHOOK_TARGET_URL")
    max_retry: int = 10
    poll_interval_seconds: int = 2
    metrics_port: int = Field(default=9102, alias="METRICS_PORT_INTEGRATION")

    model_config = {"populate_by_name": True, "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
