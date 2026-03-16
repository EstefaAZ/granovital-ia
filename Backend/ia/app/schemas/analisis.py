# ==============================================================
# modulo_04_ia / app/schemas/analisis.py
# Esquemas Pydantic - entrada y salida de todos los servicios IA
# ==============================================================

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, field_validator


# ==============================================================
# RF-05 / RF-06 - ANALISIS DE IMAGEN
# ==============================================================

class ClaseConfianza(BaseModel):
    """Una clase predicha con su probabilidad."""
    clase:       str
    probabilidad: float


class AnalisisImagenResponse(BaseModel):
    """
    Respuesta completa del analisis de imagen.
    Sigue los pasos 8-10 del Diagrama de Secuencia oficial.
    """
    id_analisis:       int
    tipo_analisis:     str
    diagnostico:       str
    confianza:         float
    confianza_pct:     str           # "92.3%" - RNF-02 amigable
    top_clases:        List[ClaseConfianza]
    recomendacion:     str
    nivel_urgencia:    str
    version_modelo:    Optional[str] = None
    tiempo_inferencia: Optional[float] = None
    tiempo_pct_rnf01:  str           # "2.3s de 5s permitidos"
    nombre_imagen:     Optional[str] = None
    fecha_analisis:    datetime
    id_cultivo:        int
    model_config = ConfigDict(from_attributes=True)


class HistorialAnalisisResponse(BaseModel):
    """Resumen para el historial de analisis (CP-07)."""
    id_analisis:    int
    tipo_analisis:  str
    diagnostico:    str
    confianza:      float
    nivel_urgencia: str
    fecha_analisis: datetime
    id_cultivo:     int
    model_config = ConfigDict(from_attributes=True)


# ==============================================================
# RF-07 - PREDICCION FITOSANITARIA
# ==============================================================

class PrediccionFitoResponse(BaseModel):
    """Resultado de la prediccion de riesgo fitosanitario."""
    id_prediccion:       int
    nivel_riesgo:        str
    probabilidad_riesgo: float
    probabilidad_pct:    str
    factores_riesgo:     List[str]
    enfermedades_prob:   Dict[str, float]
    recomendacion:       str
    # Snapshot de datos usados
    temperatura_usada:   Optional[float] = None
    humedad_usada:       Optional[float] = None
    precipitacion_usada: Optional[float] = None
    fecha_prediccion:    datetime
    id_cultivo:          int
    model_config = ConfigDict(from_attributes=True)


# ==============================================================
# RF-08 - RECOMENDACION DE RIEGO
# ==============================================================

class RecomendacionRiegoResponse(BaseModel):
    """Recomendacion de riego basada en datos del suelo y clima."""
    id_reco:             int
    necesita_riego:      str
    cantidad_litros_m2:  Optional[float] = None
    frecuencia_dias:     Optional[int] = None
    momento_optimo:      Optional[str] = None
    justificacion:       str
    recomendacion:       str
    nivel_urgencia:      str
    # Snapshot de datos usados
    humedad_suelo_usada: Optional[float] = None
    temperatura_usada:   Optional[float] = None
    precipitacion_usada: Optional[float] = None
    fecha_recomendacion: datetime
    id_cultivo:          int
    model_config = ConfigDict(from_attributes=True)


# ==============================================================
# RF-09 - RECOMENDACION DE FERTILIZACION
# ==============================================================

class RecomendacionFertResponse(BaseModel):
    """Recomendacion de fertilizacion basada en datos del suelo."""
    id_reco_fert:             int
    tipo_fertilizante:        str
    dosis_kg_ha:              Optional[float] = None
    frecuencia_aplicacion:    Optional[str] = None
    metodo_aplicacion:        Optional[str] = None
    nutrientes_deficientes:   List[str]
    justificacion:            str
    recomendacion:            str
    nivel_urgencia:           str
    # Snapshot de datos usados
    ph_suelo_usado:           Optional[float] = None
    nitrogeno_usado:          Optional[float] = None
    fosforo_usado:            Optional[float] = None
    potasio_usado:            Optional[float] = None
    materia_organica_usada:   Optional[float] = None
    fecha_recomendacion:      datetime
    id_cultivo:               int
    model_config = ConfigDict(from_attributes=True)


# ==============================================================
# RESUMEN DE DASHBOARD IA
# ==============================================================

class ResumenIAResponse(BaseModel):
    """Panel resumen del Caficultor con el estado de todos los modulos IA."""
    cultivo_id:                  int
    datos_validos_rn03:          bool
    mensaje_rn03:                str
    # Ultimo analisis imagen
    ultimo_dx_enfermedad:        Optional[str] = None
    ultima_conf_enfermedad:      Optional[float] = None
    ultimo_dx_plaga:             Optional[str] = None
    ultima_conf_plaga:           Optional[float] = None
    # Ultima prediccion fitosanitaria
    ultimo_nivel_riesgo:         Optional[str] = None
    # Ultima recomendacion de riego
    ultima_reco_riego:           Optional[str] = None
    # Ultima recomendacion de fertilizacion
    ultimo_fertilizante:         Optional[str] = None
    # Alertas activas de todos los modelos
    alertas:                     List[str] = []
    # Fechas de ultima ejecucion
    fecha_ultimo_analisis_img:   Optional[datetime] = None
    fecha_ultima_prediccion:     Optional[datetime] = None
    fecha_ultima_reco_riego:     Optional[datetime] = None
    fecha_ultima_reco_fert:      Optional[datetime] = None
