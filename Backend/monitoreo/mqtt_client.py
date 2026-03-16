# ==============================================================
# modulo_03_monitoreo / mqtt_client.py
# Suscriptor MQTT - Ingesta automatica desde sensores IoT
#
# RNF-09 Interoperabilidad con sensores IoT
# RNF-10 Protocolo ligero para zonas rurales con red limitada
#
# Topics suscritos:
#   granovital/cultivo/{id}/ambiental
#   granovital/cultivo/{id}/suelo
#
# Formato de payload esperado (JSON):
#   Ambiental: {"temperatura": 22.5, "humedad_relativa": 78.3, ...}
#   Suelo:     {"ph": 6.2, "humedad_suelo": 55.0, ...}
#
# El campo cultivo_id se extrae del topico, no del payload,
# para evitar suplantacion de identidad entre sensores.
# ==============================================================

import json
import logging
import re
from typing import Optional

import paho.mqtt.client as mqtt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.monitoreo import MonitoreoAmbiental, MonitoreoSuelo

logger = logging.getLogger(__name__)

# Patron para extraer el cultivo_id del topico MQTT
PATRON_TOPIC = re.compile(r"granovital/cultivo/(\d+)/(ambiental|suelo)")

# ID del usuario sistema que registra las lecturas IoT
USUARIO_SISTEMA_ID = 1


def _extraer_cultivo_y_tipo(topic: str) -> Optional[tuple]:
    """
    Extrae el cultivo_id y el tipo de medicion del topic MQTT.
    Retorna None si el topic no cumple el formato esperado.
    """
    coincidencia = PATRON_TOPIC.match(topic)
    if not coincidencia:
        return None
    return int(coincidencia.group(1)), coincidencia.group(2)


def _persistir_ambiental(db: Session, cultivo_id: int, payload: dict) -> None:
    """Persiste una lectura ambiental recibida desde un sensor IoT."""
    campos_permitidos = {
        "temperatura", "humedad_relativa", "precipitacion_mm",
        "radiacion_solar", "velocidad_viento",
    }
    datos = {k: v for k, v in payload.items() if k in campos_permitidos}

    if not datos:
        logger.warning(
            f"Payload ambiental sin campos validos del cultivo {cultivo_id}: "
            f"{payload}"
        )
        return

    registro = MonitoreoAmbiental(
        **datos,
        origen_dato="sensor_iot",
        id_sensor=payload.get("id_sensor"),
        observaciones=f"Ingesta automatica MQTT - sensor {payload.get('id_sensor', 'desconocido')}",
        id_cultivo=cultivo_id,
    )
    db.add(registro)
    db.commit()
    logger.info(
        f"Ambiental IoT guardado: cultivo={cultivo_id} datos={datos}"
    )


def _persistir_suelo(db: Session, cultivo_id: int, payload: dict) -> None:
    """Persiste una lectura de suelo recibida desde un sensor IoT."""
    campos_permitidos = {
        "ph", "humedad_suelo", "nitrogeno", "fosforo",
        "potasio", "materia_organica", "conductividad_ec",
    }
    datos = {k: v for k, v in payload.items() if k in campos_permitidos}

    if not datos:
        logger.warning(
            f"Payload suelo sin campos validos del cultivo {cultivo_id}: "
            f"{payload}"
        )
        return

    registro = MonitoreoSuelo(
        **datos,
        origen_dato="sensor_iot",
        id_sensor=payload.get("id_sensor"),
        observaciones=f"Ingesta automatica MQTT - sensor {payload.get('id_sensor', 'desconocido')}",
        id_cultivo=cultivo_id,
    )
    db.add(registro)
    db.commit()
    logger.info(
        f"Suelo IoT guardado: cultivo={cultivo_id} datos={datos}"
    )


# ==============================================================
# CALLBACKS MQTT
# ==============================================================

def on_connect(client, userdata, flags, rc):
    """Suscribe a los topicos de sensores al conectarse al broker."""
    if rc == 0:
        logger.info(
            f"MQTT conectado al broker "
            f"{settings.MQTT_BROKER_HOST}:{settings.MQTT_BROKER_PORT}"
        )
        client.subscribe(settings.MQTT_TOPIC_AMBIENTAL)
        client.subscribe(settings.MQTT_TOPIC_SUELO)
        logger.info(
            f"Suscrito a: {settings.MQTT_TOPIC_AMBIENTAL} | "
            f"{settings.MQTT_TOPIC_SUELO}"
        )
    else:
        logger.error(f"MQTT fallo al conectar. Codigo de error: {rc}")


def on_disconnect(client, userdata, rc):
    if rc != 0:
        logger.warning(
            f"MQTT desconectado inesperadamente (rc={rc}). "
            "Reintentando conexion automaticamente..."
        )


def on_message(client, userdata, message):
    """
    Procesa cada mensaje MQTT entrante.
    Extrae cultivo_id del topic, decodifica el JSON del payload
    y persiste la lectura en la base de datos.
    """
    topic   = message.topic
    payload = None

    try:
        payload = json.loads(message.payload.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        logger.error(f"Payload invalido en topic '{topic}': {e}")
        return

    resultado = _extraer_cultivo_y_tipo(topic)
    if resultado is None:
        logger.warning(f"Topic MQTT no reconocido: {topic}")
        return

    cultivo_id, tipo = resultado

    db: Session = SessionLocal()
    try:
        if tipo == "ambiental":
            _persistir_ambiental(db, cultivo_id, payload)
        elif tipo == "suelo":
            _persistir_suelo(db, cultivo_id, payload)
    except Exception as e:
        logger.error(
            f"Error al persistir lectura MQTT "
            f"cultivo={cultivo_id} tipo={tipo}: {e}",
            exc_info=True,
        )
        db.rollback()
    finally:
        db.close()


# ==============================================================
# INICIALIZACION DEL CLIENTE
# ==============================================================

def iniciar_cliente_mqtt() -> mqtt.Client:
    """
    Configura y conecta el cliente MQTT al broker.
    Usa loop_start() para procesamiento asincrono en segundo plano,
    lo que permite que el cliente coexista con el servidor FastAPI.
    """
    client = mqtt.Client(client_id="granovital-monitoreo-subscriber")
    client.on_connect    = on_connect
    client.on_disconnect = on_disconnect
    client.on_message    = on_message

    # Reconexion automatica configurable via paho
    client.reconnect_delay_set(min_delay=5, max_delay=60)

    try:
        client.connect(
            settings.MQTT_BROKER_HOST,
            settings.MQTT_BROKER_PORT,
            keepalive=60,
        )
        client.loop_start()
        logger.info("Cliente MQTT iniciado en modo asincrono")
    except Exception as e:
        logger.error(
            f"No se pudo conectar al broker MQTT "
            f"{settings.MQTT_BROKER_HOST}:{settings.MQTT_BROKER_PORT}. "
            f"El modulo funcionara en modo manual. Error: {e}"
        )

    return client


if __name__ == "__main__":
    # Modo standalone para pruebas de integracion IoT
    logging.basicConfig(level=logging.DEBUG)
    cliente = iniciar_cliente_mqtt()
    import time
    logger.info("Escuchando mensajes MQTT. Presione Ctrl+C para detener.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        cliente.loop_stop()
        cliente.disconnect()
        logger.info("Cliente MQTT detenido.")
