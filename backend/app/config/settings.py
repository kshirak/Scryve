"""Application settings powered by Pydantic Settings.

All configuration is sourced from environment variables (and optionally a `.env`
file) so the application stays 12-factor friendly. Importing modules should use
`get_settings()` (FastAPI dependency-injection friendly) or the module-level
`settings` singleton.
"""

from __future__ import annotations

from functools import lru_cache
from typing import List, Literal

from pydantic import Field, PostgresDsn, computed_field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Strongly-typed application settings.

    Attributes are populated from environment variables. Field names are
    case-insensitive in the underlying environment lookup.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Application ---
    app_name: str = Field(default="Scryve", alias="APP_NAME")
    app_env: Literal["development", "staging", "production", "test"] = Field(
        default="development", alias="APP_ENV"
    )
    app_debug: bool = Field(default=True, alias="APP_DEBUG")
    app_host: str = Field(default="0.0.0.0", alias="APP_HOST")
    app_port: int = Field(default=8000, alias="APP_PORT")
    api_v1_prefix: str = Field(default="/api/v1", alias="API_V1_PREFIX")

    # --- Database ---
    postgres_user: str = Field(default="scryve", alias="POSTGRES_USER")
    postgres_password: str = Field(default="scryve", alias="POSTGRES_PASSWORD")
    postgres_db: str = Field(default="scryve", alias="POSTGRES_DB")
    postgres_host: str = Field(default="localhost", alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, alias="POSTGRES_PORT")
    database_url_override: str | None = Field(default=None, alias="DATABASE_URL")

    # --- JWT ---
    jwt_secret_key: str = Field(
        default="change-me-to-a-long-random-string", alias="JWT_SECRET_KEY"
    )
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    jwt_access_token_expire_minutes: int = Field(
        default=30, alias="JWT_ACCESS_TOKEN_EXPIRE_MINUTES"
    )
    jwt_refresh_token_expire_days: int = Field(
        default=7, alias="JWT_REFRESH_TOKEN_EXPIRE_DAYS"
    )

    # --- CORS ---
    cors_allowed_origins: List[str] = Field(
        default_factory=lambda: ["http://localhost:3000"],
        alias="CORS_ALLOWED_ORIGINS",
    )

    # --- Logging ---
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO", alias="LOG_LEVEL"
    )

    # ------------------------------------------------------------------
    # Validators
    # ------------------------------------------------------------------
    @field_validator("cors_allowed_origins", mode="before")
    @classmethod
    def _split_cors_origins(cls, value: object) -> object:
        """Allow `CORS_ALLOWED_ORIGINS` to be a comma-separated string."""
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    # ------------------------------------------------------------------
    # Computed properties
    # ------------------------------------------------------------------
    @computed_field  # type: ignore[misc]
    @property
    def database_url(self) -> str:
        """Resolved SQLAlchemy database URL.

        Prefers an explicit `DATABASE_URL` env var; otherwise builds a DSN from
        the discrete Postgres fields.
        """
        if self.database_url_override:
            return self.database_url_override
        dsn = PostgresDsn.build(
            scheme="postgresql+psycopg2",
            username=self.postgres_user,
            password=self.postgres_password,
            host=self.postgres_host,
            port=self.postgres_port,
            path=self.postgres_db,
        )
        return str(dsn)

    @property
    def is_production(self) -> bool:
        """True when running in the production environment."""
        return self.app_env == "production"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached `Settings` instance.

    Using `lru_cache` ensures the `.env` file is parsed only once per process
    and makes the function trivially usable as a FastAPI dependency.

    Returns:
        Settings: The application settings singleton.
    """
    return Settings()


# Module-level convenience singleton for non-DI call sites.
settings: Settings = get_settings()
