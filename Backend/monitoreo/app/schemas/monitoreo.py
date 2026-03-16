# ==============================================================
# modulo_03_monitoreo / app/schemas/monitoreo.py
# Esquemas Pydantic - validacion de entrada y salida
#
# Los rangos de validacion estan basados en parametros
# agronomicos reales para el cultivo de cafe en Colombia:
#   - Temperatura optima: 18-24 C (acepta 0-45 C)
#   - pH optimo para cafe: 5.5-6.5 (acepta 3.0-10.0)
#   - Humedad relativa optima: 70-90% (acepta 0-100%)
# ==============================================================

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, field_validator


# ==============================================================
# MONITOREO AMBIENTAL - RF-03
# ==============================================================

class MonitoreoAmbientalCreate(BaseModel):
    """
    Datos para registrar una lectura ambiental.
    Al menos un campo de medicion debe estar presente.
    """
    temperatura:      Optional[float] = None
    humedad_relativa: Optional[float] = None
    precipitacion_mm: Optional[float] = None
    radiacion_solar:  Optional[float] = None
    velocidad_viento: Optional[float] = None
    origen_dato:      str = "manual"
    id_sensor:        Optional[int] = None
    observaciones:    Optional[str] = None

    @field_validator("temperatura")
    @classmethod
    def temperatura_rango(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and not (-10 <= v <= 55):
            raise ValueError(
                "La temperatura debe estar entre -10 y 55 grados Celsius"
            )
        return v

    @field_validator("humedad_relativa")
    @classmethod
    def humedad_rango(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and not (0 <= v <= 100):
            raise ValueError(
                "La humedad relativa debe estar entre 0 y 100 por ciento"
            )
        return v

    @field_validator("precipitacion_mm")
    @classmethod
    def precipitacion_positiva(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v < 0:
            raise ValueError("La precipitacion no puede ser negativa")
        return v

    @field_validator("radiacion_solar")
    @classmethod
    def radiacion_positiva(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v < 0:
            raise ValueError("La radiacion solar no puede ser negativa")
        return v

    @field_validator("velocidad_viento")
    @classmethod
    def viento_positivo(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v < 0:
            raise ValueError("La velocidad del viento no puede ser negativa")
        return v

    @field_validator("origen_dato")
    @classmethod
    def origen_valido(cls, v: str) -> str:
        origenes = {"sensor_iot", "manual", "api_externa"}
        if v not in origenes:
            raise ValueError(
                f"Origen '{v}' invalido. Opciones: {sorted(origenes)}"
            )
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "temperatura":      22.5,
                "humedad_relativa": 78.3,
                "precipitacion_mm": 12.0,
                "radiacion_solar":  450.0,
                "velocidad_viento": 8.5,
                "origen_dato":      "manual",
                "observaciones":    "Lectura matutina. Cielo despejado.",
            }
        }
    )


class MonitoreoAmbientalResponse(BaseModel):
    id_monitoreo:     int
    temperatura:      Optional[float] = None
    humedad_relativa: Optional[float] = None
    precipitacion_mm: Optional[float] = None
    radiacion_solar:  Optional[float] = None
    velocidad_viento: Optional[float] = None
    origen_dato:      str
    id_sensor:        Optional[int] = None
    observaciones:    Optional[str] = None
    fecha_registro:   datetime
    id_cultivo:       int
    # Alertas calculadas por el servicio
    alerta_temperatura: Optional[str] = None
    alerta_humedad:     Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


# ==============================================================
# MONITOREO DE SUELO - RF-04
# ==============================================================

class MonitoreoSueloCreate(BaseModel):
    """
    Datos para registrar una lectura del estado del suelo.
    Al menos un campo de medicion debe estar presente.
    """
    ph:               Optional[float] = None
    humedad_suelo:    Optional[float] = None
    nitrogeno:        Optional[float] = None
    fosforo:          Optional[float] = None
    potasio:          Optional[float] = None
    materia_organica: Optional[float] = None
    conductividad_ec: Optional[float] = None
    origen_dato:      str = "manual"
    id_sensor:        Optional[int] = None
    observaciones:    Optional[str] = None

    @field_validator("ph")
    @classmethod
    def ph_rango(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and not (0 <= v <= 14):
            raise ValueError(
                "El pH debe estar en la escala de 0 a 14"
            )
        return v

    @field_validator("humedad_suelo")
    @classmethod
    def humedad_rango(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and not (0 <= v <= 100):
            raise ValueError(
                "La humedad del suelo debe estar entre 0 y 100 por ciento"
            )
        return v

    @field_validator("nitrogeno", "fosforo", "potasio")
    @classmethod
    def nutriente_positivo(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v < 0:
            raise ValueError("Los valores de nutrientes no pueden ser negativos")
        return v

    @field_validator("materia_organica")
    @classmethod
    def mo_rango(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and not (0 <= v <= 100):
            raise ValueError(
                "La materia organica debe estar entre 0 y 100 por ciento"
            )
        return v

    @field_validator("origen_dato")
    @classmethod
    def origen_valido(cls, v: str) -> str:
        origenes = {"sensor_iot", "laboratorio", "manual"}
        if v not in origenes:
            raise ValueError(
                f"Origen '{v}' invalido. Opciones: {sorted(origenes)}"
            )
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "ph":               6.2,
                "humedad_suelo":    55.0,
                "nitrogeno":        28.5,
                "fosforo":          18.0,
                "potasio":          25.0,
                "materia_organica": 3.8,
                "conductividad_ec": 0.45,
                "origen_dato":      "laboratorio",
                "observaciones":    "Analisis Lab. Suelos CENICAFE. Muestra compuesta.",
            }
        }
    )


class MonitoreoSueloResponse(BaseModel):
    id_monitoreo_suelo: int
    ph:                 Optional[float] = None
    humedad_suelo:      Optional[float] = None
    nitrogeno:          Optional[float] = None
    fosforo:            Optional[float] = None
    potasio:            Optional[float] = None
    materia_organica:   Optional[float] = None
    conductividad_ec:   Optional[float] = None
    origen_dato:        str
    id_sensor:          Optional[int] = None
    observaciones:      Optional[str] = None
    fecha_registro:     datetime
    id_cultivo:         int
    # Interpretaciones calculadas por el servicio
    interpretacion_ph:      Optional[str] = None
    alerta_nutrientes:      Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


# ==============================================================
# VALIDACION RN-03
# ==============================================================

class ValidezDatosResponse(BaseModel):
    """
    Respuesta del endpoint de validacion de datos para RN-03.
    El Modulo 04 de IA consulta este endpoint antes de
    generar cualquier recomendacion automatica.
    """
    cultivo_id:          int
    ambiental_valido:    bool
    suelo_valido:        bool
    ambos_validos:       bool
    horas_limite:        int
    # Detalle de fechas
    ultima_lectura_ambiental: Optional[datetime] = None
    ultima_lectura_suelo:     Optional[datetime] = None
    horas_desde_ambiental:    Optional[float] = None
    horas_desde_suelo:        Optional[float] = None
    # Mensaje para el usuario
    mensaje:             str


# ==============================================================
# RESUMEN DE DASHBOARD
# ==============================================================

class ResumenMonitoreoResponse(BaseModel):
    """Resumen para el panel del Caficultor."""
    cultivo_id:           int
    # Ultima lectura ambiental
    ultima_temperatura:   Optional[float] = None
    ultima_humedad_rel:   Optional[float] = None
    ultima_precipitacion: Optional[float] = None
    # Ultima lectura de suelo
    ultimo_ph:            Optional[float] = None
    ultima_humedad_suelo: Optional[float] = None
    ultimo_nitrogeno:     Optional[float] = None
    # Estado de validez
    datos_validos_rn03:   bool = False
    # Alertas activas
    alertas:              List[str] = []
    # Fechas
    fecha_ultima_ambiental: Optional[datetime] = None
    fecha_ultima_suelo:     Optional[datetime] = None
