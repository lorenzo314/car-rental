"""
Application configuration.

All settings are loaded from environment variables (or a .env file).
Import `settings` wherever you need a config value — never read
os.environ directly in application code.

Usage
-----
    from app.config import settings

    engine = create_engine(settings.db_url)
"""

from functools import lru_cache

from pydantic import EmailStr, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed, validated application settings.

    Values are read from environment variables.  A .env file in the
    project root is loaded automatically when present.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # -- Database ----------------------------------------------------------
    db_host: str = "localhost"
    db_port: int = 3306
    db_name: str = "car_rental"
    db_user: str = "car_rental_user"
    db_password: str = ""

    # -- Application -------------------------------------------------------
    app_env: str = "development"
    app_host: str = "localhost"
    app_port: int = 8000
    app_secret_key: str = "change_me_in_production"  # noqa: S105
    debug: bool = True

    # -- Email (Resend) ----------------------------------------------------
    resend_api_key: str = ""
    email_from: EmailStr = "noreply@example.com"
    email_from_name: str = "Car Rental"

    # -- Locale / currency -------------------------------------------------
    default_currency: str = "EUR"
    default_country: str = "France"

    # -- Computed ----------------------------------------------------------
    @computed_field
    @property
    def db_url(self) -> str:
        """SQLAlchemy connection string for MySQL."""
        return (
            f"mysql+pymysql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
            "?charset=utf8mb4"
        )

    @computed_field
    @property
    def db_url_async(self) -> str:
        """Async SQLAlchemy connection string (aiomysql driver)."""
        return (
            f"mysql+aiomysql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
            "?charset=utf8mb4"
        )

    @computed_field
    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance.

    Using lru_cache means the .env file is read exactly once per process.
    In tests, call get_settings.cache_clear() to reload after patching env vars.
    """
    return Settings()


# Module-level singleton — convenient for direct imports
settings: Settings = get_settings()
