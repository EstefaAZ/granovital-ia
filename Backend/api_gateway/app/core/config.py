# =============================================================
# api_gateway / app/core/config.py
# =============================================================

from pydantic_settings import BaseSettings
from pydantic import SecretStr, model_validator
from functools import lru_cache


class Settings(BaseSettings):

    APP_NAME: str = "GranoVital IA — API Gateway"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    GATEWAY_PORT: int = 8000

    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    # BUG-002 FIX: SecretStr evita que la clave aparezca en logs/repr.
    # Sin valor por defecto — DEBE configurarse en .env.
    JWT_SECRET_KEY: SecretStr
    JWT_ALGORITHM: str = "HS256"

    @model_validator(mode="after")
    def _validar_secretos(self) -> "Settings":
        key = self.JWT_SECRET_KEY.get_secret_value()
        if not key or key in ("cambia-esta-clave-en-produccion",):
            raise ValueError(
                "JWT_SECRET_KEY no está configurada. "
                "Define la variable en el archivo .env del api_gateway."
            )
        return self

    URL_AUTH:         str = "http://localhost:8001"
    URL_CULTIVOS:     str = "http://localhost:8002"
    URL_MONITOREO:    str = "http://localhost:8003"
    URL_IA:           str = "http://localhost:8004"
    URL_TRAZABILIDAD: str = "http://localhost:8005"
    URL_MERCADO:      str = "http://localhost:8006"
    URL_REPORTES:     str = "http://localhost:8007"

    TIMEOUT_SERVICIOS: float = 30.0

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
