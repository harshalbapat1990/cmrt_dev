from pathlib import Path
from typing import Literal, Optional

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).parent.parent / ".env.local"),
        extra="allow",
    )

    app_name: str = "CMRT"
    app_env: str = "dev"
    database_url: str = ""
    app_debug: bool = False

    auth_mode: Literal["local_jwt", "forwarded_identity"] = "forwarded_identity"

    jwt_secret: str  # Required — must be set via JWT_SECRET env var; no insecure default
    jwt_algorithm: str = "HS256"
    jwt_issuer: str = "cmrt-local"
    jwt_audience: str = "cmrt-api"
    jwt_expire_minutes: int = 60

    cors_origins: str = "http://localhost:5173"

    super_admin_email: str  # Required — must be set via SUPER_ADMIN_EMAIL env var
    super_admin_password: Optional[str] = None  # Required only in local_jwt mode

    @model_validator(mode="after")
    def _validate_auth_config(self) -> "Settings":
        if self.auth_mode == "local_jwt" and self.app_env != "local":
            raise ValueError("local_jwt auth mode is only allowed when APP_ENV=local")
        if self.auth_mode == "local_jwt" and not self.super_admin_password:
            raise ValueError("SUPER_ADMIN_PASSWORD is required in local_jwt mode")
        return self

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()