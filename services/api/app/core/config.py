from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Video Analytics API"
    app_version: str = "1.0.0"

    database_url: str = Field(
        default="postgresql+psycopg2://video_app:video_app_password@postgres:5432/video_analytics",
        alias="DATABASE_URL",
    )

    jwt_secret_key: str = Field(
        default="change_this_secret_key_change_this_secret_key_1234",
        alias="JWT_SECRET_KEY",
        min_length=32,
    )
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(default=15, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(default=7, alias="REFRESH_TOKEN_EXPIRE_DAYS")

    default_admin_username: str = Field(default="admin", alias="DEFAULT_ADMIN_USERNAME")
    default_admin_password: str = Field(default="admin12345", alias="DEFAULT_ADMIN_PASSWORD")

    cors_origins: str = Field(default="http://localhost:4173,http://ui:4173", alias="CORS_ORIGINS")

    demo_drone_enabled: bool = Field(default=False, alias="DEMO_DRONE_ENABLED")
    demo_drone_camera_name: str = Field(default="demo-drone-video", alias="DEMO_DRONE_CAMERA_NAME")
    demo_drone_source: str = Field(default="/app/videos/V_DRONE_009.mp4", alias="DEMO_DRONE_SOURCE")
    demo_drone_resolution: str = Field(default="640x512", alias="DEMO_DRONE_RESOLUTION")
    demo_drone_fps_target: int = Field(default=10, alias="DEMO_DRONE_FPS_TARGET")
    demo_drone_exclusive: bool = Field(default=True, alias="DEMO_DRONE_EXCLUSIVE")

    model_config = {"populate_by_name": True, "extra": "ignore"}

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
