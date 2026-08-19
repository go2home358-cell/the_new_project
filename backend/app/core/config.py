from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Science Study API"
    api_v1_prefix: str = "/api/v1"
    environment: str = Field(default="development")

    # Credentials come from the environment (.env); defaults carry no password.
    database_url: str = Field(default="postgresql+psycopg2://science@localhost:5432/science_study")
    test_database_url: str = Field(default="postgresql+psycopg2://science@localhost:5432/science_study_test")

    jwt_secret_key: str = Field(default="")
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 30

    admin_email: str = "admin@sciencestudy.app"
    admin_password: str = ""
    admin_name: str = "Administrator"

    ai_provider: str = "openai"
    ai_api_key: str = ""
    ai_model: str = "gpt-4o-mini"
    ai_base_url: str = "https://api.openai.com/v1"

    google_client_id: str = ""

    cors_origins: str = "*"
    upload_dir: str = "uploads"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def ai_enabled(self) -> bool:
        return bool(self.ai_api_key)


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    if not settings.jwt_secret_key:
        if settings.environment == "production":
            raise RuntimeError("JWT_SECRET_KEY must be set outside development")
        # Ephemeral development key: tokens are invalidated on every restart.
        import secrets

        settings.jwt_secret_key = secrets.token_urlsafe(48)
    return settings


settings = get_settings()
