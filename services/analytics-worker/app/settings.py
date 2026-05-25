from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = Field(
        default="postgresql+psycopg2://video_app:video_app_password@postgres:5432/video_analytics",
        alias="DATABASE_URL",
    )
    metrics_port: int = Field(default=9101, alias="METRICS_PORT_ANALYTICS")
    camera_refresh_seconds: int = Field(default=15, alias="CAMERA_REFRESH_SECONDS")
    rules_refresh_seconds: int = Field(default=10, alias="RULES_REFRESH_SECONDS")
    reconnect_backoff_seconds: int = Field(default=3, alias="RECONNECT_BACKOFF_SECONDS")
    detector_model: str = Field(default="yolov8n.pt", alias="DETECTOR_MODEL")
    detector_classes: str = Field(default="person,car,bus,truck,motorcycle", alias="DETECTOR_CLASSES")
    detector_confidence: float = Field(default=0.25, alias="DETECTOR_CONFIDENCE")
    use_mock_detector: bool = Field(default=False, alias="USE_MOCK_DETECTOR")

    model_config = {"populate_by_name": True, "extra": "ignore"}

    @property
    def allowed_classes(self) -> set[str]:
        return {x.strip() for x in self.detector_classes.split(",") if x.strip()}


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
