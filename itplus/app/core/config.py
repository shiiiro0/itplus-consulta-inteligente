"""Application configuration from environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "ITPlus Consulta Inteligente"
    secret_key: str = "change-me-in-production"
    debug: bool = True

    database_url: str = "postgresql://itplus:itplus@localhost:5432/consulta_db"
    redis_url: str = "redis://localhost:6379/0"

    ai_driver: str = "groq"
    ai_base_url: str = "https://api.groq.com/openai/v1"
    ai_api_key: str = ""
    ai_model: str = "llama-3.3-70b-versatile"
    ai_temperature: float = 0.15
    ai_max_tokens: int = 1536

    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dimensions: int = 384

    upload_dir: str = "./uploads"
    max_upload_mb: int = 20

    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = ""

    access_token_expire_minutes: int = 60 * 24

    # Azure AD / Entra ID (inactive until env vars are set)
    azure_tenant_id: str = ""
    azure_client_id: str = ""
    api_token_expire_hours: int = 24
    sessions_idle_minutes: int = 30
    sessions_retention_months: int = 6


@lru_cache
def get_settings() -> Settings:
    return Settings()
