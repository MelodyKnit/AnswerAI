import os
from functools import lru_cache
from pathlib import Path

from pydantic_settings import SettingsConfigDict, BaseSettings


BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
APP_ENV = os.getenv("APP_ENV", "dev").lower()
ENV_FILES = {
    "dev": BASE_DIR / ".env.dev",
    "prod": BASE_DIR / ".env.prod",
}
DEFAULT_ENV_FILE = ENV_FILES.get(APP_ENV, ENV_FILES["dev"])


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(DEFAULT_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    project_name: str = "AI考试答题平台后端"
    api_v1_prefix: str = "/api/v1"
    secret_key: str = "change-this-secret-key-in-production"
    access_token_expire_minutes: int = 60 * 24
    database_url: str = f"sqlite:///{(DATA_DIR / 'app.db').as_posix()}"
    openai_api_key: str | None = None
    debug: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
