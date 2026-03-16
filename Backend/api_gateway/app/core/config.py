# =============================================================
# api_gateway / app/core/config.py
# =============================================================

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):

    APP_NAME: str = "GranoVital IA — API Gateway"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    GATEWAY_PORT: int = 8000

    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    JWT_SECRET_KEY: str = "dev_secret_key_cambiar_en_produccion"
    JWT_ALGORITHM: str = "HS256"

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
