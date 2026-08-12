"""Application configuration — everything comes from environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Hisab"
    app_env: str = "development"
    secret_key: str = "dev-insecure-secret-change-me"
    access_token_expire_minutes: int = 1440

    database_url: str = "sqlite:///./hisab.db"

    cors_origins: str = "*"

    default_usd_to_pkr: float = 280.0

    @property
    def cors_origin_list(self) -> list[str]:
        if self.cors_origins.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def jwt_algorithm(self) -> str:
        return "HS256"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
