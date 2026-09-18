"""Application configuration from environment variables."""

import logging
from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

_DEFAULT_SECRET_KEY = "change-me-in-production"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "ITPlus Consulta Inteligente"
    secret_key: str = _DEFAULT_SECRET_KEY
    # Controla si Swagger (/api/docs), ReDoc (/api/redoc) y el schema OpenAPI
    # quedan expuestos (ver run_itplus.py) — antes esta flag existía pero no
    # se usaba en ningún lado ("decorativa").
    debug: bool = True

    database_url: str = "postgresql://itplus:itplus@localhost:5432/consulta_db"
    redis_url: str = "redis://localhost:6379/0"

    ai_driver: str = "gemini"
    ai_base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai/"
    ai_api_key: str = ""
    ai_model: str = "gemini-2.5-flash"
    ai_temperature: float = 0.15
    # Gemini 3 Flash es un modelo "thinking": consume tokens razonando antes de
    # responder, así que el presupuesto debe cubrir razonamiento + respuesta.
    ai_max_tokens: int = 4096
    # Sin esto, una llamada colgada al proveedor LLM podía agotar el pool de
    # threads de toda la API bajo carga (el cliente OpenAI SDK no tiene
    # timeout por defecto para requests que nunca responden).
    ai_timeout_seconds: float = 60.0

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

    @model_validator(mode="after")
    def _validate_secret_key(self) -> "Settings":
        # Con el valor por defecto, cualquiera puede leer el código fuente
        # (o adivinarlo) y forjar un JWT de administrador válido. Fallamos
        # al arranque en vez de dejar la app corriendo insegura en silencio.
        if self.secret_key == _DEFAULT_SECRET_KEY or not self.secret_key.strip():
            raise ValueError(
                "SECRET_KEY no está configurada (o usa el valor por defecto "
                f"'{_DEFAULT_SECRET_KEY}'). Define una SECRET_KEY única y "
                "secreta en el entorno o en el .env antes de arrancar la app."
            )
        if len(self.secret_key) < 16:
            # No bloqueamos el arranque por esto (no queremos adivinar
            # requisitos de longitud sin conocer el valor real), pero sí
            # avisamos fuerte: un SECRET_KEY corto es más fácil de forzar
            # por fuerza bruta.
            logger.warning(
                "SECRET_KEY tiene menos de 16 caracteres — se recomienda "
                "usar una clave más larga y aleatoria (p. ej. "
                "`openssl rand -hex 32`)."
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
