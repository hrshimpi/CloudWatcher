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

    # Used for the root-cause guess sent in Slack alerts. If unset, alerting
    # falls straight back to the templated (numbers-only) explanation.
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.0-flash"
    llm_timeout_seconds: float = 10.0

    slack_timeout_seconds: float = 5.0

    # Safe-by-default: without this, a misconfigured alert_config row would
    # start posting real Slack messages the moment someone runs detection.
    alerts_dry_run: bool = True

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
