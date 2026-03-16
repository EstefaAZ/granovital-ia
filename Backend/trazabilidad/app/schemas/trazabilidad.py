# ==============================================================
# modulo_05_trazabilidad / app/schemas/trazabilidad.py
# Esquemas Pydantic — entrada y salida de todos los endpoints
# ==============================================================

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, field_validator


# ==============================================================
# RF-10 — TRAZABILIDAD DEL LOTE
# ==============================================================

class LoteCreate(BaseModel):
    """Datos para registrar un nuevo lote de cafe. CP-04."""
    variedad_cafe:         str
    fecha_cosecha:         datetime
    metodo_cosecha:        str = "manual_selectiva"
    kg_cereza_cosechados:  float
    metodo_beneficio:      Optional[str]  = None
    observaciones:         Optional[str]  = None
    id_cultivo:            int

    @field_validator("variedad_cafe")
    @classmethod
    def variedad_valida(cls, v):
        permitidas = {"castillo", "colombia", "caturra", "cenicafe_1", "otro"}
        if v not in permitidas:
            raise ValueError(f"Variedad invalida. Use: {', '.join(sorted(permitidas))}")
        return v

    @field_validator("metodo_cosecha")
    @classmethod
    def metodo_cosecha_valido(cls, v):
        permitidos = {"manual_selectiva", "manual_global", "mecanica"}
        if v not in permitidos:
            raise ValueError(f"Metodo invalido. Use: {', '.join(sorted(permitidos))}")
        return v

    @field_validator("kg_cereza_cosechados")
    @classmethod
    def kg_positivos(cls, v):
        if v <= 0:
            raise ValueError("Los kilogramos cosechados deben ser mayores a cero.")
        return v


class LoteUpdate(BaseModel):
    """
    Actualizacion parcial — solo campos de proceso.
    RN-04: una vez el lote esta 'aprobado' o 'vendido',
    estos cambios son rechazados por el servicio para usuarios
    que no son Administrador.
    """
    metodo_beneficio:      Optional[str]   = None
    fecha_inicio_secado:   Optional[datetime] = None
    fecha_fin_secado:      Optional[datetime] = None
    kg_pergamino_seco:     Optional[float]  = None
    precio_venta_kg:       Optional[float]  = None
    comprador:             Optional[str]    = None
    fecha_venta:           Optional[datetime] = None
    destino_exportacion:   Optional[str]    = None
    observaciones:         Optional[str]    = None


class LoteResponse(BaseModel):
    """Respuesta completa del lote con todos sus datos."""
    id_lote:               int
    codigo_lote:           str
    variedad_cafe:         str
    fecha_cosecha:         datetime
    metodo_cosecha:        str
    kg_cereza_cosechados:  float
    metodo_beneficio:      Optional[str]  = None
    kg_pergamino_seco:     Optional[float] = None
    humedad_final_pct:     Optional[float] = None
    clasificacion_calidad: str
    puntaje_taza:          Optional[float] = None
    numero_defectos:       Optional[int]   = None
    precio_venta_kg:       Optional[float] = None
    comprador:             Optional[str]   = None
    fecha_venta:           Optional[datetime] = None
    destino_exportacion:   Optional[str]   = None
    estado:                str
    validado:              bool
    codigo_qr:             Optional[str]   = None
    hash_integridad:       Optional[str]   = None
    observaciones:         Optional[str]   = None
    id_cultivo:            int
    fecha_creacion:        datetime
    fecha_actualizacion:   Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class LotePublicoResponse(BaseModel):
    """
    RN-05: vista publica del lote para el consumidor.
    Solo expone informacion de trazabilidad y calidad,
    sin datos internos (precios, usuarios, IDs internos).
    """
    codigo_lote:           str
    variedad_cafe:         str
    fecha_cosecha:         str               # Solo fecha, no hora exacta
    region_origen:         Optional[str] = None
    metodo_cosecha:        str
    metodo_beneficio:      Optional[str] = None
    clasificacion_calidad: str
    puntaje_taza:          Optional[float] = None
    aprobado_exportacion:  bool
    destino_exportacion:   Optional[str]  = None
    mensaje_calidad:       str


class TransicionEstadoResponse(BaseModel):
    """Resultado de una transicion de estado del lote."""
    id_lote:        int
    codigo_lote:    str
    estado_anterior: str
    estado_nuevo:   str
    mensaje:        str
    hash_generado:  Optional[str] = None


# ==============================================================
# RF-11 — CONTROL DE SECADO
# ==============================================================

class SecadoCreate(BaseModel):
    """Registro de una lectura del proceso de secado."""
    temperatura_c:        float
    humedad_grano_pct:    Optional[float] = None
    humedad_ambiente_pct: Optional[float] = None
    horas_transcurridas:  int
    metodo_secado:        str = "solar"
    observaciones:        Optional[str]  = None

    @field_validator("temperatura_c")
    @classmethod
    def temp_rango(cls, v):
        if not (-5.0 <= v <= 80.0):
            raise ValueError("Temperatura fuera de rango fisicamente posible (-5 a 80 C).")
        return v

    @field_validator("horas_transcurridas")
    @classmethod
    def horas_positivas(cls, v):
        if v < 0:
            raise ValueError("Las horas transcurridas no pueden ser negativas.")
        return v

    @field_validator("humedad_grano_pct")
    @classmethod
    def humedad_rango(cls, v):
        if v is not None and not (0.0 <= v <= 100.0):
            raise ValueError("Humedad del grano debe estar entre 0 y 100%.")
        return v

    @field_validator("metodo_secado")
    @classmethod
    def metodo_valido(cls, v):
        if v not in {"solar", "mecanico", "mixto"}:
            raise ValueError("Metodo de secado invalido. Use: solar, mecanico o mixto.")
        return v


class SecadoResponse(BaseModel):
    """Resultado de una lectura de secado con alertas calculadas."""
    id_secado:            int
    temperatura_c:        float
    humedad_grano_pct:    Optional[float] = None
    humedad_ambiente_pct: Optional[float] = None
    horas_transcurridas:  int
    metodo_secado:        str
    alerta_temperatura:   Optional[str]  = None
    alerta_humedad:       Optional[str]  = None
    proceso_completo:     bool
    progreso_humedad_pct: Optional[float] = None  # % hacia la meta de 11%
    horas_restantes_est:  Optional[int]  = None   # estimacion si hay tendencia
    observaciones:        Optional[str]  = None
    id_lote:              int
    fecha_lectura:        datetime
    model_config = ConfigDict(from_attributes=True)


class ResumenSecadoResponse(BaseModel):
    """Resumen del estado del proceso de secado de un lote."""
    id_lote:                 int
    codigo_lote:             str
    total_lecturas:          int
    horas_totales:           int
    temp_promedio:           Optional[float] = None
    temp_ultima:             Optional[float] = None
    humedad_actual:          Optional[float] = None
    humedad_objetivo:        float
    proceso_completo:        bool
    cumple_horas_minimas:    bool
    alertas_activas:         List[str] = []
    recomendacion:           str


# ==============================================================
# RF-12 — CLASIFICACION DEL GRANO
# ==============================================================

class ClasificacionCreate(BaseModel):
    """Datos de entrada para clasificar un lote de cafe."""
    numero_defectos:       int
    humedad_pct:           float
    puntaje_taza:          Optional[float] = None
    factores_calidad:      Optional[str]   = None
    observaciones_calidad: Optional[str]   = None
    metodo:                str = "ia_automatica"

    @field_validator("numero_defectos")
    @classmethod
    def defectos_positivos(cls, v):
        if v < 0:
            raise ValueError("El numero de defectos no puede ser negativo.")
        return v

    @field_validator("humedad_pct")
    @classmethod
    def humedad_rango(cls, v):
        if not (0.0 <= v <= 30.0):
            raise ValueError("Humedad del grano fuera de rango (0-30%).")
        return v

    @field_validator("puntaje_taza")
    @classmethod
    def puntaje_rango(cls, v):
        if v is not None and not (0.0 <= v <= 100.0):
            raise ValueError("Puntaje de taza debe estar entre 0 y 100.")
        return v

    @field_validator("metodo")
    @classmethod
    def metodo_valido(cls, v):
        if v not in {"ia_automatica", "manual", "laboratorio"}:
            raise ValueError("Metodo invalido. Use: ia_automatica, manual o laboratorio.")
        return v


class ClasificacionResponse(BaseModel):
    """Resultado completo de la clasificacion del grano."""
    id_clasificacion:       int
    categoria:              str
    categoria_legible:      str       # "Cafe Excelso Extra" — RNF-02
    numero_defectos:        int
    humedad_pct:            float
    puntaje_taza:           Optional[float] = None
    precio_sugerido_kg:     Optional[float] = None
    aprobado_exportacion:   bool
    metodo:                 str
    confianza_ia:           Optional[float] = None
    descripcion_categoria:  str
    recomendacion:          str
    estado_lote_nuevo:      str      # estado resultante del diagrama
    id_lote:                int
    fecha_clasificacion:    datetime
    model_config = ConfigDict(from_attributes=True)


# ==============================================================
# EVENTO DE TRAZABILIDAD
# ==============================================================

class EventoResponse(BaseModel):
    """Un evento del log de trazabilidad del lote."""
    id_evento:          int
    tipo_evento:        str
    estado_anterior:    Optional[str] = None
    estado_nuevo:       Optional[str] = None
    descripcion:        str
    id_lote:            int
    id_usuario:         int
    fecha_evento:       datetime
    model_config = ConfigDict(from_attributes=True)
