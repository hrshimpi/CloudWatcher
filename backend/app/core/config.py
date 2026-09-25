from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "CloudWatcher"
    environment: str = "development"

    postgres_user: str = "cloudwatcher"
    postgres_password: str = "cloudwatcher"
    postgres_host: str = "localhost"
    postgres_port: int = 5434
    postgres_db: str = "cloudwatcher"

    # Set in Cloud Run to connect via the Cloud SQL Auth Proxy's Unix socket
    # (mounted at /cloudsql/<connection_name>) instead of TCP host:port. Takes
    # precedence over postgres_host/postgres_port when set; leave unset for
    # local dev / Docker Compose, which use plain TCP.
    postgres_socket_dir: str | None = None

    # Used for the root-cause guess sent in Slack alerts. If unset, alerting
    # falls straight back to the templated (numbers-only) explanation.
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.0-flash"
    llm_timeout_seconds: float = 10.0

    slack_timeout_seconds: float = 5.0

    # Deploy-time default webhook (e.g. from Secret Manager in production).
    # Only used when nobody has configured a global alert_config row yet via
    # the Settings UI / PUT /config/thresholds -- the DB always wins once it
    # has one. Without this, a fresh deploy alerts nowhere until someone
    # visits Settings once.
    slack_webhook_url: str | None = None

    # Safe-by-default: without this, a misconfigured alert_config row would
    # start posting real Slack messages the moment someone runs detection.
    alerts_dry_run: bool = True

    @property
    def database_url(self) -> str:
        if self.postgres_socket_dir:
            return (
                f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
                f"@/{self.postgres_db}?host={self.postgres_socket_dir}"
            )
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
