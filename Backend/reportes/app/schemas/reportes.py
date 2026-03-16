# ==============================================================
# modulo_07_reportes / app/schemas/reportes.py
# Esquemas Pydantic — RF-18
# ==============================================================

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, field_validator


# ==============================================================
# REPORTES
# ==============================================================

TIPOS_VALIDOS = {
    "cultivos", "trazabilidad", "fitosanitario",
    "ambiental", "mercado", "usuarios", "general",
}

class ReporteSolicitud(BaseModel):
    """Cuerpo de la petición para solicitar un reporte."""
    tipo_reporte: str
    nombre:       Optional[str] = None  # Si None, se genera automáticamente
    fecha_inicio: Optional[datetime] = None
    fecha_fin:    Optional[datetime] = None

    @field_validator("tipo_reporte")
    @classmethod
    def tipo_valido(cls, v):
        if v not in TIPOS_VALIDOS:
            raise ValueError(
                f"Tipo inválido. Use uno de: {', '.join(sorted(TIPOS_VALIDOS))}"
            )
        return v

    @field_validator("fecha_fin")
    @classmethod
    def fin_posterior_a_inicio(cls, v, info):
        inicio = info.data.get("fecha_inicio")
        if v and inicio and v <= inicio:
            raise ValueError("fecha_fin debe ser posterior a fecha_inicio.")
        return v


class ReporteResponse(BaseModel):
    """Respuesta con el estado y metadata del reporte."""
    id_reporte:     int
    tipo_reporte:   str
    nombre:         str
    estado:         str
    estado_label:   str           # texto legible para la interfaz (RNF-02)
    ruta_archivo:   Optional[str]
    nombre_archivo: Optional[str]
    tamano_kb:      Optional[float]   # en KB para la interfaz
    num_registros:  Optional[int]
    mensaje_error:  Optional[str]
    nombre_usuario: Optional[str]
    fecha_solicitud: datetime
    fecha_generado:  Optional[datetime]
    fecha_descarga:  Optional[datetime]
    model_config = ConfigDict(from_attributes=True)


class ReporteListItem(BaseModel):
    """Item del listado de reportes para la tabla del Administrador."""
    id_reporte:    int
    tipo_reporte:  str
    nombre:        str
    estado:        str
    estado_label:  str
    tamano_kb:     Optional[float]
    num_registros: Optional[int]
    nombre_usuario: Optional[str]
    fecha_solicitud: datetime
    fecha_generado:  Optional[datetime]
    model_config = ConfigDict(from_attributes=True)


# ==============================================================
# AUDITORÍA
# ==============================================================

class AuditoriaCreate(BaseModel):
    """
    Esquema interno para registrar un evento de auditoría.
    Usado por otros módulos del sistema que llamen al servicio.
    """
    modulo:        str
    accion:        str
    tipo_entidad:  Optional[str]  = None
    id_entidad:    Optional[int]  = None
    descripcion:   str
    resultado:     str            = "exitoso"
    id_usuario:    Optional[int]  = None
    nombre_usuario: Optional[str] = None
    rol_usuario:   Optional[str]  = None
    ip_origen:     Optional[str]  = None
    dato_anterior: Optional[str]  = None
    dato_nuevo:    Optional[str]  = None


class AuditoriaResponse(BaseModel):
    """Registro de auditoría para consulta del Administrador."""
    id_auditoria:  int
    modulo:        str
    accion:        str
    tipo_entidad:  Optional[str]
    id_entidad:    Optional[int]
    descripcion:   str
    resultado:     str
    id_usuario:    Optional[int]
    nombre_usuario: Optional[str]
    rol_usuario:   Optional[str]
    ip_origen:     Optional[str]
    dato_anterior: Optional[str]
    dato_nuevo:    Optional[str]
    fecha_evento:  datetime
    model_config = ConfigDict(from_attributes=True)


class AuditoriaFiltros(BaseModel):
    """Filtros de búsqueda en el log de auditoría."""
    modulo:     Optional[str]     = None
    accion:     Optional[str]     = None
    resultado:  Optional[str]     = None
    id_usuario: Optional[int]     = None
    fecha_desde: Optional[datetime] = None
    fecha_hasta: Optional[datetime] = None
    page:       int = 1
    page_size:  int = 50


# ==============================================================
# ESTADÍSTICAS GLOBALES (para el panel del Administrador)
# ==============================================================

class ResumenSistemaResponse(BaseModel):
    """Métricas globales del sistema para el Administrador."""
    # Usuarios
    total_usuarios:      int
    usuarios_activos:    int
    # Cultivos
    total_cultivos:      int
    total_lotes:         int
    # IA
    total_analisis_ia:   int
    analisis_ultima_semana: int
    # Trazabilidad
    lotes_en_proceso:    int
    lotes_vendidos:      int
    # Mercado
    total_analisis_precio:  int
    total_analisis_demanda: int
    # Auditoría
    eventos_auditoria_hoy:  int
    errores_sistema_semana: int
    # Reportes
    reportes_generados:     int
    fecha_actualizacion:    datetime
