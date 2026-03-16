# ==============================================================
# modulo_02_cultivos / app/core/config.py
# Configuracion del modulo de Gestion de Cultivos y Lotes
# RF-03 Gestion de cultivos | RF-04 Registro de lotes
# RN-02 Trazabilidad obligatoria | RNF-04 Seguridad JWT
# ==============================================================

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME:    str = "GranoVital IA - Modulo Cultivos y Lotes"
    APP_VERSION: str = "1.0.0"
    DEBUG:       bool = False

    # Base de datos compartida con todos los modulos
    DATABASE_URL: str = (
        "mysql+pymysql://granovital:granovital123@localhost:3306/granovital_db"
    )

    # JWT - se valida el token emitido por el Modulo 01
    SECRET_KEY: str = "cambia-esta-clave-en-produccion"
    ALGORITHM:  str = "HS256"

    # CORS
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
