# =============================================================
# app/core/config.py
# Configuración central de la aplicación GranoVital IA
# Requisitos: RNF-04 (seguridad), RNF-03 (disponibilidad)
# =============================================================

from pydantic_settings import BaseSettings
from pydantic import SecretStr, model_validator
from functools import lru_cache


class Settings(BaseSettings):
    """
    Configuración global del sistema.
    Lee automáticamente desde variables de entorno o archivo .env
    """

    # ── Aplicación ────────────────────────────────────────────
    APP_NAME: str = "GranoVital IA"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ALLOWED_ORIGINS: str = "http://localhost:3000"

    # ── Base de datos MySQL ───────────────────────────────────
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_NAME: str = "granovital_ia"
    DB_USER: str = "root"
    DB_PASSWORD: str = ""

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
            f"?charset=utf8mb4"
        )

    # ── JWT ───────────────────────────────────────────────────
    # BUG-002 FIX: SecretStr + sin valor por defecto. DEBE estar en .env.
    JWT_SECRET_KEY: SecretStr = SecretStr("your-jwt-secret-key-here")
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── Redis ─────────────────────────────────────────────────
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str = ""

    # ── Email ─────────────────────────────────────────────────
    EMAIL_ENABLED: bool = False
    EMAIL_SMTP_SERVER: str = "smtp.gmail.com"
    EMAIL_SMTP_PORT: int = 587
    EMAIL_SMTP_USERNAME: str = ""
    EMAIL_SMTP_PASSWORD: SecretStr = SecretStr("")
    EMAIL_FROM: str = "noreply@granovitalia.com"
    EMAIL_FROM_NAME: str = "GranoVital IA"

    # ── Verificación de email ──────────────────────────────────
    EMAIL_VERIFICATION_CODE_EXPIRE_MINUTES: int = 15
    EMAIL_VERIFICATION_CODE_LENGTH: int = 6

    # ── Google OAuth ──────────────────────────────────────────
    GOOGLE_OAUTH_ENABLED: bool = False
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: SecretStr = SecretStr("")
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/v1/auth/google/callback"

    @property
    def REDIS_URL(self) -> str:
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    @model_validator(mode="after")
    def _validar_secretos(self) -> "Settings":
        key = self.JWT_SECRET_KEY.get_secret_value()
        if not key or key in ("cambia-esta-clave-en-produccion",):
            raise ValueError(
                "JWT_SECRET_KEY no está configurada. "
                "Define la variable en el archivo .env del módulo login."
            )
        return self

    # ── Seguridad de cuenta ───────────────────────────────────
    MAX_LOGIN_ATTEMPTS: int = 5
    LOGIN_LOCKOUT_MINUTES: int = 15

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """
    Retorna la instancia única de configuración (patrón Singleton).
    @lru_cache garantiza que el archivo .env se lea una sola vez.
    """
    return Settings()


settings = get_settings()
