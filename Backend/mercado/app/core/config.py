# ==============================================================
# modulo_06_mercado / app/core/config.py
#
# RF-13  Análisis de precios del café para decisiones comerciales
# RF-14  Análisis de demanda del mercado
# RN-01  Acceso restringido por rol (solo Comercializador y Admin)
# RNF-01 Respuesta < 5 segundos en todos los análisis
# RNF-02 Interfaz legible para usuarios sin perfil técnico
# ==============================================================

from pydantic_settings import BaseSettings
from pydantic import SecretStr


class Settings(BaseSettings):
    APP_NAME:    str  = "GranoVital IA - Modulo Mercado"
    APP_VERSION: str  = "1.0.0"
    DEBUG:       bool = False

    # BUG-003 FIX: credenciales en .env, nunca en código fuente
    DATABASE_URL: str
    # BUG-001 FIX: sin valor por defecto — DEBE definirse en .env
    SECRET_KEY: SecretStr
    ALGORITHM:  str = "HS256"
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    # RF-13: rango historico para calcular tendencia (meses hacia atras)
    MESES_HISTORICO_PRECIO: int = 12

    # RF-14: meses para calcular tendencia de demanda
    MESES_HISTORICO_DEMANDA: int = 6

    # Variacion de precio que activa alerta al Comercializador (porcentaje)
    UMBRAL_VARIACION_ALERTA_PCT: float = 5.0

    # Precio base de referencia FNC (COP/kg pergamino seco) — actualizable
    PRECIO_BASE_FNC_COP: float = 5200.0

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
