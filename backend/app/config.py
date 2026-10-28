"""Application settings, read from environment variables."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed settings. Each field maps to an env var of the same name (case-insensitive).

    A local `.env` file is also read, either in `backend/` or the project root.
    """

    model_config = SettingsConfigDict(env_file=(".env", "../.env"), extra="ignore")

    database_url: str = "postgresql+psycopg://fightnight:fightnight@localhost:5433/fightnight"


settings = Settings()
