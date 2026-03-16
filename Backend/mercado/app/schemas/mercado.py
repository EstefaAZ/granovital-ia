# ==============================================================
# modulo_06_mercado / app/schemas/mercado.py
# Esquemas Pydantic — RF-13 y RF-14
# ==============================================================

from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, ConfigDict, field_validator


# ==============================================================
# RF-13 — PRECIOS
# ==============================================================

class PrecioCreate(BaseModel):
    """Registro manual de un precio de referencia de mercado."""
    fuente:            str
    tipo_cafe:         str   = "pergamino_seco"
    precio_cop_kg:     float
    precio_usd_lb:     Optional[float] = None
    variedad:          Optional[str]   = None
    categoria_calidad: str   = "todas"
    region:            Optional[str]   = None
    notas:             Optional[str]   = None
    fecha_precio:      datetime

    @field_validator("precio_cop_kg")
    @classmethod
    def precio_positivo(cls, v):
        if v <= 0:
            raise ValueError("El precio debe ser mayor que cero.")
        return v

    @field_validator("fuente")
    @classmethod
    def fuente_valida(cls, v):
        validas = {"fnc", "bolsa_ny", "mercado_local", "manual", "propio_sistema"}
        if v not in validas:
            raise ValueError(f"Fuente invalida. Use: {', '.join(sorted(validas))}")
        return v

    @field_validator("tipo_cafe")
    @classmethod
    def tipo_valido(cls, v):
        validos = {"pergamino_seco", "verde_exportacion", "tostado", "especial"}
        if v not in validos:
            raise ValueError(f"Tipo invalido. Use: {', '.join(sorted(validos))}")
        return v


class PrecioResponse(BaseModel):
    id_precio:         int
    fuente:            str
    tipo_cafe:         str
    precio_cop_kg:     float
    precio_usd_lb:     Optional[float] = None
    variedad:          Optional[str]   = None
    categoria_calidad: str
    region:            Optional[str]   = None
    notas:             Optional[str]   = None
    id_lote_origen:    Optional[int]   = None
    fecha_precio:      datetime
    fecha_registro:    datetime
    model_config = ConfigDict(from_attributes=True)


class AnalisisPrecioResponse(BaseModel):
    """Resultado del análisis estadístico de precios - RF-13."""
    id_analisis:         int
    periodo_inicio:      datetime
    periodo_fin:         datetime
    tipo_cafe:           str
    fuente_analizada:    str
    precio_promedio:     float
    precio_minimo:       float
    precio_maximo:       float
    rango_precios:       float               # maximo - minimo
    variacion_pct:       Optional[float]
    variacion_label:     Optional[str]       # "+3.2% vs mes anterior" — RNF-02
    tendencia:           str
    tendencia_icono:     str                 # ↑ ↓ → ~
    precio_proyectado:   Optional[float]
    alerta_activa:       bool
    mensaje_alerta:      Optional[str]
    recomendacion:       str
    num_registros_base:  int
    interpretacion:      str                 # texto legible para no técnicos
    fecha_analisis:      datetime
    model_config = ConfigDict(from_attributes=True)


class HistorialPrecioItem(BaseModel):
    """Un punto del histórico de precios para graficar."""
    mes:           str          # "2025-06"
    precio_prom:   float
    precio_fnc:    Optional[float]
    precio_propio: Optional[float]
    num_registros: int


# ==============================================================
# RF-14 — DEMANDA
# ==============================================================

class DemandaObservacionCreate(BaseModel):
    """Registro de observación de demanda externa por el Comercializador."""
    observaciones_mercado: Optional[str] = None
    oportunidades:         Optional[str] = None
    riesgos:               Optional[str] = None


class AnalisisDemandaResponse(BaseModel):
    """Resultado del análisis de demanda del período - RF-14."""
    id_demanda:              int
    periodo_inicio:          datetime
    periodo_fin:             datetime
    total_lotes_vendidos:    int
    kg_totales_vendidos:     float
    kg_promedio_por_lote:    Optional[float]
    dias_promedio_venta:     Optional[float]
    categoria_mas_demandada: Optional[str]
    comprador_frecuente:     Optional[str]
    destino_principal:       Optional[str]
    nivel_demanda:           str
    nivel_demanda_label:     str              # "Demanda Alta ↑"
    variacion_demanda_pct:   Optional[float]
    variacion_label:         Optional[str]
    observaciones_mercado:   Optional[str]
    oportunidades:           Optional[str]
    riesgos:                 Optional[str]
    recomendacion:           str
    interpretacion:          str
    fecha_analisis:          datetime
    model_config = ConfigDict(from_attributes=True)


# ==============================================================
# DASHBOARD MERCADO
# ==============================================================

class DashboardMercadoResponse(BaseModel):
    """Panel consolidado para el Comercializador."""
    # Precios
    precio_actual_cop:        Optional[float]
    precio_fnc_referencia:    Optional[float]
    diferencial_fnc_pct:      Optional[float]   # % sobre/bajo precio FNC
    tendencia_precio:         Optional[str]
    alerta_precio:            bool
    mensaje_alerta_precio:    Optional[str]
    # Demanda
    lotes_disponibles:        int               # lotes en estado 'aprobado'
    kg_disponibles:           float             # kg disponibles para venta
    total_vendido_mes:        int
    kg_vendidos_mes:          float
    nivel_demanda_actual:     Optional[str]
    # Proyección
    precio_proyectado_mes:    Optional[float]
    recomendacion_comercial:  str
    # Alertas combinadas
    alertas:                  List[str]
    fecha_actualizacion:      datetime
