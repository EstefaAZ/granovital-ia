# ==============================================================
# modulo_03_monitoreo / app/models/monitoreo.py
# ORM SQLAlchemy - tbl_monitoreo_ambiental, tbl_monitoreo_suelo
#
# Trazabilidad de requisitos:
#   RF-03  Registrar y mostrar variables ambientales del cultivo
#          - temperatura, humedad relativa, precipitacion,
#            radiacion solar, velocidad del viento
#   RF-04  Mostrar estado del suelo
#          - pH, humedad, nitrogeno, fosforo, potasio,
#            materia organica, conductividad electrica
#   RN-03  Los datos deben estar actualizados para que el
#          modulo de IA genere recomendaciones (validado por
#          el campo fecha_registro vs HORAS_DATOS_VALIDOS)
#   RNF-09 El campo origen_dato distingue si la lectura vino
#          de un sensor IoT, de ingreso manual del caficultor
#          o de una API meteorologica externa
#   RNF-10 El origen 'manual' permite operar sin conectividad
#          IoT en zonas rurales con limitaciones de red
# ==============================================================

from datetime import datetime
from sqlalchemy import (
    Column, Integer, DateTime, Numeric,
    Enum, ForeignKey, String, Text,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class MonitoreoAmbiental(Base):
    """
    tbl_monitoreo_ambiental - Serie de tiempo de variables
    climaticas del entorno del cultivo.

    Cada registro representa una lectura puntual. El sistema
    puede recibir lecturas automaticas de sensores IoT via MQTT
    o ingresos manuales del caficultor cuando no hay red.

    Variables capturadas segun RF-03:
      - temperatura        Celsius
      - humedad_relativa   porcentaje (0-100)
      - precipitacion_mm   milimetros de lluvia
      - radiacion_solar    W/m2
      - velocidad_viento   km/h

    El Modulo 04 de IA consume la ultima lectura de esta
    tabla para predicciones fitosanitarias (RF-07) y
    recomendaciones de riego (RF-08).
    RN-03: si la ultima lectura supera HORAS_DATOS_VALIDOS
    horas, el modulo de IA rechaza generar recomendaciones.
    """
    __tablename__ = "tbl_monitoreo_ambiental"

    id_monitoreo      = Column(Integer, primary_key=True, autoincrement=True)
    temperatura       = Column(
        Numeric(5, 2), nullable=True,
        comment="Temperatura ambiental en grados Celsius"
    )
    humedad_relativa  = Column(
        Numeric(5, 2), nullable=True,
        comment="Humedad relativa del aire en porcentaje (0-100)"
    )
    precipitacion_mm  = Column(
        Numeric(7, 2), nullable=True,
        comment="Precipitacion acumulada en milimetros"
    )
    radiacion_solar   = Column(
        Numeric(8, 2), nullable=True,
        comment="Radiacion solar incidente en W/m2"
    )
    velocidad_viento  = Column(
        Numeric(6, 2), nullable=True,
        comment="Velocidad del viento en km/h"
    )
    origen_dato       = Column(
        Enum("sensor_iot", "manual", "api_externa"),
        nullable=False,
        default="manual",
        comment=(
            "sensor_iot: MQTT automatico | "
            "manual: ingreso del caficultor (RNF-10) | "
            "api_externa: servicio meteorologico (RNF-09)"
        ),
    )
    id_sensor         = Column(
        Integer, nullable=True,
        comment="ID del sensor que genero la lectura (nulo si es manual)"
    )
    observaciones     = Column(Text, nullable=True)
    fecha_registro    = Column(
        DateTime, nullable=False, default=datetime.utcnow,
        comment="Marca de tiempo UTC de la lectura - clave para RN-03"
    )
    id_cultivo = Column(
    Integer,
    # BUG-038 FIX: use_alter=True innecesario sin referencia circular real
    ForeignKey("tbl_cultivo.id_cultivo", ondelete="CASCADE"),
    nullable=False,
    )

    def __repr__(self) -> str:
        return (
            f"<MonitoreoAmbiental id={self.id_monitoreo} "
            f"cultivo={self.id_cultivo} "
            f"temp={self.temperatura}C hum={self.humedad_relativa}%>"
        )


class MonitoreoSuelo(Base):
    """
    tbl_monitoreo_suelo - Serie de tiempo del estado
    fisicoquimico del suelo del cultivo.

    Variables capturadas segun RF-04:
      - ph                  escala 0-14
      - humedad_suelo       porcentaje volumetrico (0-100)
      - nitrogeno           mg/kg
      - fosforo             mg/kg
      - potasio             mg/kg
      - materia_organica    porcentaje (0-100)
      - conductividad_ec    dS/m (conductividad electrica)

    El Modulo 04 de IA consume la ultima lectura de esta
    tabla para recomendaciones de fertilizacion (RF-09).
    RN-03: si la ultima lectura supera HORAS_DATOS_VALIDOS
    horas, el modulo de IA rechaza generar recomendaciones.
    """
    __tablename__ = "tbl_monitoreo_suelo"

    id_monitoreo_suelo = Column(Integer, primary_key=True, autoincrement=True)
    ph                 = Column(
        Numeric(4, 2), nullable=True,
        comment="Potencial de hidrogeno del suelo (escala 0-14)"
    )
    humedad_suelo      = Column(
        Numeric(5, 2), nullable=True,
        comment="Humedad volumetrica del suelo en porcentaje (0-100)"
    )
    nitrogeno          = Column(
        Numeric(8, 2), nullable=True,
        comment="Nitrogeno disponible en mg/kg"
    )
    fosforo            = Column(
        Numeric(8, 2), nullable=True,
        comment="Fosforo disponible en mg/kg"
    )
    potasio            = Column(
        Numeric(8, 2), nullable=True,
        comment="Potasio disponible en mg/kg"
    )
    materia_organica   = Column(
        Numeric(5, 2), nullable=True,
        comment="Contenido de materia organica en porcentaje"
    )
    conductividad_ec   = Column(
        Numeric(6, 3), nullable=True,
        comment="Conductividad electrica del suelo en dS/m"
    )
    origen_dato        = Column(
        Enum("sensor_iot", "laboratorio", "manual"),
        nullable=False,
        default="manual",
        comment=(
            "sensor_iot: lectura automatica | "
            "laboratorio: analisis de suelo certificado | "
            "manual: ingreso del caficultor (RNF-10)"
        ),
    )
    id_sensor          = Column(
        Integer, nullable=True,
        comment="ID del sensor IoT que genero la lectura"
    )
    observaciones      = Column(Text, nullable=True)
    fecha_registro     = Column(
        DateTime, nullable=False, default=datetime.utcnow,
        comment="Marca de tiempo UTC de la lectura - clave para RN-03"
    )
    id_cultivo = Column(
    Integer,
    # BUG-038 FIX: use_alter=True innecesario sin referencia circular real
    ForeignKey("tbl_cultivo.id_cultivo", ondelete="CASCADE"),
    nullable=False,
    )

    def __repr__(self) -> str:
        return (
            f"<MonitoreoSuelo id={self.id_monitoreo_suelo} "
            f"cultivo={self.id_cultivo} "
            f"pH={self.ph} hum={self.humedad_suelo}%>"
        )
