"""Application settings, read from environment variables."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed settings. Each field maps to an env var of the same name (case-insensitive).

    A local `.env` file is also read, either in `backend/` or the project root.
    """

    model_config = SettingsConfigDict(env_file=(".env", "../.env"), extra="ignore")

    database_url: str = "postgresql+psycopg://fightnight:fightnight@localhost:5433/fightnight"

    # Scraper politeness settings
    scraper_cache_dir: str = "data/cache"
    scraper_delay_seconds: float = 1.0  # minimum gap between real HTTP requests
    scraper_cache_hours: float = 24.0  # re-download a page once its cached copy is older than this
    # Required by Wikipedia's User-Agent policy: an email or URL where you can be reached.
    scraper_contact: str = ""


settings = Settings()
