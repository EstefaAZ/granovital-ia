# ==============================================================
# modulo_02_cultivos / app/core/config.py
# Configuracion del modulo de Gestion de Cultivos y Lotes
# RF-03 Gestion de cultivos | RF-04 Registro de lotes
# RN-02 Trazabilidad obligatoria | RNF-04 Seguridad JWT
# ==============================================================

from pydantic_settings import BaseSettings
from pydantic import SecretStr


class Settings(BaseSettings):
    APP_NAME:    str = "GranoVital IA - Modulo Cultivos y Lotes"
    APP_VERSION: str = "1.0.0"
    DEBUG:       bool = False

    # Base de datos compartida con todos los modulos
    # BUG-003 FIX: credenciales en .env, nunca en código fuente
    DATABASE_URL: str = "sqlite:///./granovital_cultivos.db"

    # JWT - se valida el token emitido por el Modulo 01
    # BUG-001 FIX: sin valor por defecto — DEBE definirse en .env
    SECRET_KEY: SecretStr = SecretStr("your-secret-key-here")
    ALGORITHM:  str = "HS256"

    # CORS
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
