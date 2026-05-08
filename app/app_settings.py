"""Pydantic-settings layer over .env.

Each class group corresponds to one slice of Django/Celery/app config.
All values can be overridden by env vars or `.env` file at repo root.
"""
from pathlib import Path
from urllib.parse import urlparse

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent


class DjangoSettings(BaseSettings):
    """Django core settings sourced from environment."""

    DJANGO_SECRET_KEY: str = Field(
        ...,
        description="Cryptographic key for signing sessions, CSRF tokens, password resets. Required. Never commit. Generate via `python -c 'import secrets; print(secrets.token_urlsafe(50))'`.",
    )
    DJANGO_DEBUG: bool = Field(
        False,
        description="Enable Django debug mode (verbose errors, no template caching). NEVER true in production.",
    )
    PORT: int = Field(
        8000,
        description="HTTP port the app listens on. Used to derive default CSRF_TRUSTED_ORIGINS for localhost.",
    )
    ALLOWED_HOSTS: list[str] = Field(
        ["localhost", "127.0.0.1"],
        description="Hostnames Django will serve. Reject Host headers not in this list. Set to your domain in prod.",
    )
    CSRF_TRUSTED_ORIGINS: list[str] = Field(
        ["http://localhost:8000", "http://127.0.0.1:8000"],
        description="Origins (scheme + host[:port]) trusted for CSRF. Each explicit port must match $PORT.",
    )

    @model_validator(mode="after")
    def _check_csrf_origin_ports(self):
        for origin in self.CSRF_TRUSTED_ORIGINS:
            parsed = urlparse(origin)
            if parsed.port is not None and parsed.port != self.PORT:
                raise ValueError(
                    f"CSRF_TRUSTED_ORIGINS entry {origin!r} has port {parsed.port} "
                    f"but PORT={self.PORT}. Align them or omit the port."
                )
        return self

    class Config:
        env_file = ".env"
        extra = "ignore"


class CelerySettings(BaseSettings):
    """Celery + Redis broker settings.

    REDIS_URL is composed from host/port/db so docker-compose can reuse the
    same port var.
    """

    REDIS_HOST: str = Field(
        "127.0.0.1",
        description="Redis hostname. Use service name (e.g. 'redis') when running in compose network.",
    )
    REDIS_HOST_PORT: int = Field(
        6379,
        description="Redis port on host. Reused by docker-compose for the published port mapping.",
    )
    REDIS_DB: int = Field(
        0,
        description="Redis logical DB number (0-15). Use separate DBs per env to isolate keys.",
    )
    CELERY_TASK_TRACK_STARTED: bool = Field(
        True,
        description="Mark tasks as STARTED when worker picks them up (in addition to PENDING/SUCCESS/etc).",
    )
    CELERY_TIMEZONE: str = Field(
        "UTC",
        description="Timezone for Celery beat schedule evaluation. Always UTC unless you have a hard reason.",
    )

    @property
    def REDIS_URL(self) -> str:
        """Composed redis:// URL. Used as both broker and result backend."""
        return f"redis://{self.REDIS_HOST}:{self.REDIS_HOST_PORT}/{self.REDIS_DB}"

    class Config:
        env_file = ".env"
        extra = "ignore"


class ClaudeSettings(BaseSettings):
    """Path + behavior for the local `claude` CLI."""

    CLAUDE_BIN: str = Field(
        "claude",
        description="Path to claude CLI binary. Defaults to PATH lookup. Override if installed in a non-standard location.",
    )

    class Config:
        env_file = ".env"
        extra = "ignore"


class AppSettings(DjangoSettings, CelerySettings, ClaudeSettings, BaseSettings):
    """Aggregate of all settings groups. Single instance: `APP_SETTINGS`."""

    class Config:
        env_file = ".env"
        extra = "ignore"


APP_SETTINGS = AppSettings()
