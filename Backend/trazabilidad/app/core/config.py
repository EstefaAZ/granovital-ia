# ==============================================================
# modulo_05_trazabilidad / app/core/config.py
#
# RF-10  Trazabilidad del lote: cosecha → proceso → venta
# RF-11  Control de secado: temperatura y tiempo
# RF-12  Clasificacion del grano por calidad (IA)
# RF-15  Consulta publica via QR (RN-05)
# RN-02  Trazabilidad obligatoria antes de comercializar
# RN-04  Inmutabilidad de registros validados
# RNF-05 Integridad de datos de trazabilidad
# ==============================================================

from pydantic_settings import BaseSettings
from pydantic import SecretStr


class Settings(BaseSettings):
    APP_NAME:    str  = "GranoVital IA - Modulo Trazabilidad"
    APP_VERSION: str  = "1.0.0"
    DEBUG:       bool = False

    # BUG-003 FIX: credenciales en .env, nunca en código fuente
    DATABASE_URL: str

    # BUG-001 FIX: sin valor por defecto — DEBE definirse en .env
    SECRET_KEY: SecretStr
    ALGORITHM:  str = "HS256"

    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    # URL base del sistema - se usa para armar el QR publico (RN-05)
    URL_BASE_SISTEMA: str = "http://localhost:3000"

    # RN-04: prefijo del hash de integridad de cada registro validado
    HASH_INTEGRIDAD_SAL: str = "granovital-trazabilidad-2025"

    # RF-11: umbrales de secado (CENICAFE - parametros optimos)
    # Temperatura optima: 35-45 C; tiempo minimo: 72 horas
    SECADO_TEMP_MIN_OPTIMA: float = 35.0
    SECADO_TEMP_MAX_OPTIMA: float = 45.0
    SECADO_TEMP_CRITICA:    float = 55.0   # quema el grano
    SECADO_HORAS_MINIMAS:   int   = 72     # horas minimas para cafe pergamino
    SECADO_HUMEDAD_OBJETIVO: float = 11.0  # % humedad final objetivo CENICAFE

    # RF-12: umbrales de clasificacion del grano
    HUMEDAD_MAX_EXPORTACION: float = 12.0  # % max para exportacion FNC
    DEFECTOS_MAX_SUPREMO:    int   = 0     # cero defectos = supremo
    DEFECTOS_MAX_EXTRA:      int   = 4     # maximo defectos excelso extra
    DEFECTOS_MAX_EXCELSO:    int   = 8     # maximo defectos excelso

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
