"""Application settings."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings for the backend."""

    app_name: str = "telesco-pi"
    app_version: str = "0.1.0"
    environment: Literal["development", "test", "production"] = "development"
    api_v1_prefix: str = "/api/v1"
    host: str = "127.0.0.1"
    port: int = 8000
    allow_lan_bind: bool = False
    cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ]
    )
    trusted_hosts: list[str] = Field(default_factory=lambda: ["localhost", "127.0.0.1", "testserver"])
    auth_token: str | None = None
    enable_auth_token: bool = False
    log_level: str = "INFO"
    request_id_header: str = "X-Request-ID"
    data_dir: Path | None = None
    database_url: str | None = None
    retention_days: int = 30
    auto_restore_last_session: bool = True
    scheduler_heartbeat_seconds: int = 15
    device_mode: Literal["simulator", "stub"] = "simulator"
    mount_driver: Literal["simulated", "az_go2_stub"] = "simulated"
    camera_driver: Literal["simulated", "player_one_mars_m_stub"] = "simulated"
    simulation_frame_width: int = 640
    simulation_frame_height: int = 480

    model_config = SettingsConfigDict(
        env_prefix="TELESCO_PI_",
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )

    @model_validator(mode="after")
    def _resolve_paths(self) -> "Settings":
        if self.data_dir is None:
            self.data_dir = (
                Path(".runtime-data")
                if self.environment in {"development", "test"}
                else Path("/var/lib/telesco-pi")
            )

        if self.database_url is None:
            self.database_url = f"sqlite:///{self.data_dir / 'telesco-pi.sqlite3'}"

        return self

    @property
    def bind_host(self) -> str:
        if self.host == "0.0.0.0" and not self.allow_lan_bind:
            return "127.0.0.1"
        return self.host
