import os
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field
from pydantic_settings import SettingsConfigDict, BaseSettings


BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
UPLOADS_DIR = DATA_DIR / "uploads"
PROMPTS_DIR = BASE_DIR / "prompts"
APP_ENV = os.getenv("APP_ENV", "dev").lower()
ENV_FILES = {
    "dev": BASE_DIR / ".env.dev",
    "prod": BASE_DIR / ".env.prod",
}
DEFAULT_ENV_FILE = ENV_FILES.get(APP_ENV, ENV_FILES["dev"])


class LLMConfig(BaseModel):
    name: str
    url: str
    key: str
    model: str
    supports_functools: bool = False
    multi_modal: bool = False


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
    llm_configs: list[LLMConfig] = Field(default_factory=list)
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"])
    teacher_invite_code: str = "dev-teacher-invite"
    debug: bool = True


@lru_cache
def get_settings() -> Settings:
    """
    获取 settings 相关数据。
    """
    return Settings()


settings = get_settings()
