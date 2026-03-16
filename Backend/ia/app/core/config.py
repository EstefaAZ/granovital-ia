# ==============================================================
# modulo_04_ia / app/core/config.py
# Configuracion del Modulo de Inteligencia Artificial
#
# RF-05  Deteccion de enfermedades por imagen (CNN)
# RF-06  Deteccion de plagas por imagen (CNN/YOLO)
# RF-07  Prediccion fitosanitaria (datos ambientales)
# RF-08  Recomendacion de riego (datos suelo + ambiente)
# RF-09  Recomendacion de fertilizacion (datos suelo)
# RN-03  Solo opera con datos actualizados del M03
# RNF-01 Respuesta en menos de 5 segundos
# RNF-08 Actualizacion de modelos sin afectar operacion
# ==============================================================

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME:    str = "GranoVital IA - Modulo Inteligencia Artificial"
    APP_VERSION: str = "1.0.0"
    DEBUG:       bool = False

    DATABASE_URL: str = (
        "mysql+pymysql://granovital:granovital123@localhost:3306/granovital_db"
    )

    SECRET_KEY: str = "cambia-esta-clave-en-produccion"
    ALGORITHM:  str = "HS256"

    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    # URL interna del Modulo 03 para verificar RN-03
    URL_MODULO_MONITOREO: str = "http://localhost:8003/api/v1"

    # RNF-01 - tiempo maximo de inferencia en segundos
    TIMEOUT_INFERENCIA_SEG: float = 4.5

    # Tamano maximo de imagen para analisis (bytes) - 10 MB
    IMAGEN_MAX_BYTES: int = 10_485_760

    # Tipos de imagen permitidos
    IMAGEN_TIPOS_PERMITIDOS: str = "image/jpeg,image/png,image/webp"

    # Directorio donde se guardan los modelos entrenados
    # RNF-08: permite swap de modelos en caliente
    DIR_MODELOS: str = "app/ia/modelos"

    # Umbral minimo de confianza para reportar un diagnostico
    UMBRAL_CONFIANZA_MINIMA: float = 0.60

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
