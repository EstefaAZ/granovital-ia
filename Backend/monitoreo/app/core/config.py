# ==============================================================
# modulo_03_monitoreo / app/core/config.py
# Configuracion del modulo de Monitoreo Ambiental y de Suelo
#
# RF-03  Monitoreo ambiental - variables del entorno del cultivo
# RF-04  Monitoreo de suelo  - pH, humedad, nutrientes
# RN-03  Solo se generan recomendaciones con datos actualizados
# RNF-09 Interoperabilidad con sensores IoT via MQTT
# RNF-10 Operacion en zonas rurales con conectividad limitada
# ==============================================================

from pydantic_settings import BaseSettings
from pydantic import SecretStr


class Settings(BaseSettings):
    APP_NAME:    str = "GranoVital IA - Modulo Monitoreo"
    APP_VERSION: str = "1.0.0"
    DEBUG:       bool = False

    # Base de datos compartida con todos los modulos
    # BUG-003 FIX: credenciales en .env, nunca en código fuente
    DATABASE_URL: str

    # JWT - validado desde el token emitido por Modulo 01
    # BUG-001 FIX: sin valor por defecto — DEBE definirse en .env
    SECRET_KEY: SecretStr
    ALGORITHM:  str = "HS256"

    # CORS
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    # RN-03 - umbral en horas para datos validos
    # Si la ultima lectura supera este valor, el modulo de IA
    # rechazara generar recomendaciones automaticas
    HORAS_DATOS_VALIDOS: int = 24

    # MQTT - RNF-09 interoperabilidad con sensores IoT
    MQTT_BROKER_HOST: str = "localhost"
    MQTT_BROKER_PORT: int = 1883
    MQTT_TOPIC_AMBIENTAL: str = "granovital/cultivo/+/ambiental"
    MQTT_TOPIC_SUELO:     str = "granovital/cultivo/+/suelo"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
