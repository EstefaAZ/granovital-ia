# ==============================================================
# modulo_02_cultivos / app/schemas/cultivo.py
# Esquemas Pydantic - validacion de entrada y salida
# RF-03 Cultivos | RF-04 Lotes | RNF-02 Usabilidad
# Mensajes de error en espanol para usuarios sin perfil tecnico
# ==============================================================

import re
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator


# ==============================================================
# CULTIVO - RF-03
# ==============================================================

class CultivoCreate(BaseModel):
    """Datos necesarios para registrar un nuevo cultivo."""
    nombre_cultivo: str
    ubicacion:      Optional[str] = None
    area_hectareas: Optional[float] = None
    variedad_cafe:  Optional[str] = None
    fecha_siembra:  Optional[datetime] = None
    observaciones:  Optional[str] = None

    @field_validator("nombre_cultivo")
    @classmethod
    def nombre_valido(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 3:
            raise ValueError(
                "El nombre del cultivo debe tener al menos 3 caracteres"
            )
        if len(v) > 120:
            raise ValueError(
                "El nombre del cultivo no puede superar 120 caracteres"
            )
        return v

    @field_validator("area_hectareas")
    @classmethod
    def area_positiva(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v <= 0:
            raise ValueError("El area en hectareas debe ser mayor que cero")
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "nombre_cultivo": "Finca La Esperanza",
                "ubicacion":      "6.2530N 75.5736W - Vereda El Chuscal, Andes, Antioquia",
                "area_hectareas": 3.5,
                "variedad_cafe":  "Castillo",
                "fecha_siembra":  "2023-03-15T00:00:00",
                "observaciones":  "Lote en zona de ladera con sombrio natural",
            }
        }
    )


class CultivoUpdate(BaseModel):
    """Actualizacion parcial de un cultivo. Todos los campos son opcionales."""
    nombre_cultivo: Optional[str] = None
    ubicacion:      Optional[str] = None
    area_hectareas: Optional[float] = None
    variedad_cafe:  Optional[str] = None
    observaciones:  Optional[str] = None
    estado:         Optional[str] = None

    @field_validator("estado")
    @classmethod
    def estado_permitido(cls, v: Optional[str]) -> Optional[str]:
        estados = {
            "creado", "en_seguimiento",
            "con_problema_detectado", "tratamiento_aplicado",
            "finalizado", "eliminado",
        }
        if v and v not in estados:
            raise ValueError(
                f"Estado '{v}' no valido. Opciones disponibles: {sorted(estados)}"
            )
        return v

    @field_validator("area_hectareas")
    @classmethod
    def area_positiva(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v <= 0:
            raise ValueError("El area en hectareas debe ser mayor que cero")
        return v


class CultivoResponse(BaseModel):
    """Respuesta completa del cultivo para el frontend."""
    id_cultivo:     int
    nombre_cultivo: str
    ubicacion:      Optional[str] = None
    area_hectareas: Optional[float] = None
    variedad_cafe:  Optional[str] = None
    fecha_siembra:  Optional[datetime] = None
    estado:         str
    observaciones:  Optional[str] = None
    fecha_registro: datetime
    id_usuario:     int
    total_lotes:    int = 0
    total_sensores: int = 0
    model_config = ConfigDict(from_attributes=True)


# ==============================================================
# LOTE - RF-04
# ==============================================================

class LoteCreate(BaseModel):
    """Datos para registrar un nuevo lote de produccion."""
    codigo_lote:   str
    fecha_cosecha: Optional[datetime] = None
    cantidad_kg:   Optional[float] = None
    observaciones: Optional[str] = None

    @field_validator("codigo_lote")
    @classmethod
    def codigo_formato_valido(cls, v: str) -> str:
        v = v.strip().upper()
        patron = r"^[A-Z0-9\-]{3,50}$"
        if not re.match(patron, v):
            raise ValueError(
                "El codigo del lote solo puede contener letras mayusculas, "
                "numeros y guiones. Ejemplo: LOT-2025-001"
            )
        return v

    @field_validator("cantidad_kg")
    @classmethod
    def cantidad_positiva(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v <= 0:
            raise ValueError("La cantidad en kilogramos debe ser mayor que cero")
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "codigo_lote":   "LOT-2025-001",
                "fecha_cosecha": "2025-06-10T08:00:00",
                "cantidad_kg":   450.0,
                "observaciones": "Cosecha selectiva. Madurez optima 90%.",
            }
        }
    )


class LoteUpdate(BaseModel):
    """Actualizacion parcial del lote. Todos los campos son opcionales."""
    estado_lote:   Optional[str] = None
    cantidad_kg:   Optional[float] = None
    observaciones: Optional[str] = None

    @field_validator("estado_lote")
    @classmethod
    def estado_valido(cls, v: Optional[str]) -> Optional[str]:
        estados = {
            "registrado", "disponible", "en_analisis",
            "aprobado", "con_problema", "vendido", "eliminado",
        }
        if v and v not in estados:
            raise ValueError(
                f"Estado '{v}' no valido. Opciones disponibles: {sorted(estados)}"
            )
        return v


class LoteResponse(BaseModel):
    """Respuesta completa del lote para el frontend."""
    id_lote:       int
    codigo_lote:   str
    codigo_qr:     Optional[str] = None
    fecha_cosecha: Optional[datetime] = None
    cantidad_kg:   Optional[float] = None
    estado_lote:   str
    observaciones: Optional[str] = None
    fecha_registro: datetime
    id_cultivo:    int
    model_config = ConfigDict(from_attributes=True)


# ==============================================================
# SENSOR - RNF-06, RNF-09
# ==============================================================

class SensorCreate(BaseModel):
    """Datos para registrar un nuevo sensor IoT en el cultivo."""
    codigo_sensor:     str
    tipo_sensor:       str
    descripcion:       Optional[str] = None
    unidad_medida:     Optional[str] = None
    fecha_instalacion: Optional[datetime] = None

    @field_validator("tipo_sensor")
    @classmethod
    def tipo_valido(cls, v: str) -> str:
        tipos = {"temperatura", "humedad", "suelo", "radiacion", "multivariable"}
        if v not in tipos:
            raise ValueError(
                f"Tipo de sensor '{v}' no valido. Opciones: {sorted(tipos)}"
            )
        return v

    @field_validator("codigo_sensor")
    @classmethod
    def codigo_no_vacio(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("El codigo del sensor no puede estar vacio")
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "codigo_sensor":     "SNS-TEMP-001",
                "tipo_sensor":       "temperatura",
                "descripcion":       "Sensor de temperatura ambiental DHT22",
                "unidad_medida":     "C",
                "fecha_instalacion": "2025-01-20T00:00:00",
            }
        }
    )


class SensorResponse(BaseModel):
    """Respuesta completa del sensor para el frontend."""
    id_sensor:         int
    codigo_sensor:     str
    tipo_sensor:       str
    descripcion:       Optional[str] = None
    unidad_medida:     Optional[str] = None
    fecha_instalacion: Optional[datetime] = None
    estado:            str
    id_cultivo:        int
    model_config = ConfigDict(from_attributes=True)


# ==============================================================
# RESUMEN DEL DASHBOARD
# ==============================================================

class ResumenCultivoResponse(BaseModel):
    """Resumen rapido para el panel principal del Caficultor."""
    total_cultivos_activos: int
    total_lotes:            int
    lotes_en_proceso:       int
    lotes_vendidos:         int
    lotes_con_problema:     int
    area_total_hectareas:   float
