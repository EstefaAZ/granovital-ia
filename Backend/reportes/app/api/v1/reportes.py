# ==============================================================
# modulo_07_reportes / app/api/v1/reportes.py
# Router FastAPI — RF-18
#
# Endpoints:
#   GET    /reportes/resumen              Panel global del sistema
#   POST   /reportes                      Solicitar nuevo reporte
#   GET    /reportes                      Listar reportes generados
#   GET    /reportes/{id}                 Consultar estado de reporte
#   GET    /reportes/{id}/descargar       Descargar archivo PDF
#   POST   /reportes/{id}/reintentar      Reintentar reporte en error
#   POST   /auditoria                     Registrar evento de auditoría
#   GET    /auditoria                     Consultar log de auditoría
#   DELETE /auditoria  → NO EXPUESTO (RNF-05 append-only)
#
# Roles autorizados: solo Administrador (RN-01, RF-18)
# ==============================================================

from typing import List, Optional
from fastapi import APIRouter, Depends, Query, Request, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_rol, get_current_user_id, require_roles
from app.schemas.reportes import (
    AuditoriaCreate,
    AuditoriaFiltros,
    AuditoriaResponse,
    ReporteListItem,
    ReporteResponse,
    ReporteSolicitud,
    ResumenSistemaResponse,
)
from app.services.reportes_service import ReportesService

router = APIRouter(prefix="/reportes", tags=["Reportes y Auditoría"])
SOLO_ADMIN  = ("Administrador",)
# F-R04 FIX: Comercializador puede ver sus propios reportes de mercado
ADMIN_O_COMERCIALIZADOR = ("Administrador", "Comercializador")


@router.get(
    "/resumen",
    response_model=ResumenSistemaResponse,
    summary="RF-18: Resumen ejecutivo global del sistema",
    description=(
        "Retorna métricas de todos los módulos: usuarios, cultivos, análisis IA, "
        "trazabilidad, mercado, auditoría y reportes. "
        "Exclusivo del Administrador (RN-01)."
    ),
)
def resumen_sistema(
    _rol: str     = Depends(require_roles(*SOLO_ADMIN)),
    db:   Session = Depends(get_db),
) -> ResumenSistemaResponse:
    return ReportesService(db).resumen_sistema()


@router.post(
    "",
    response_model=ReporteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="RF-18: Solicitar generación de un reporte",
    description=(
        "Inicia el ciclo de vida del reporte siguiendo el diagrama de estados "
        "oficial: Solicitado → Generando → Disponible (o Error). "
        "Tipos disponibles: general, cultivos, trazabilidad, fitosanitario, "
        "ambiental, mercado, usuarios."
    ),
)
def solicitar_reporte(
    solicitud:  ReporteSolicitud,
    request:    Request,
    usuario_id: int = Depends(get_current_user_id),
    _rol:       str = Depends(require_roles(*SOLO_ADMIN)),
    db:         Session = Depends(get_db),
) -> ReporteResponse:
    # Obtener nombre del usuario del token (si viene)
    nombre_usuario = request.headers.get("X-Usuario-Nombre", "Administrador")
    return ReportesService(db).solicitar_reporte(solicitud, usuario_id, nombre_usuario)


@router.get(
    "",
    response_model=List[ReporteListItem],
    summary="RF-18: Listar reportes generados",
)
def listar_reportes(
    usuario_id: int     = Depends(get_current_user_id),
    _rol:       str     = Depends(require_roles(*SOLO_ADMIN)),
    db:         Session = Depends(get_db),
) -> List[ReporteListItem]:
    return ReportesService(db).listar_reportes(usuario_id)


@router.get(
    "/{id_reporte}",
    response_model=ReporteResponse,
    summary="RF-18: Consultar estado de un reporte",
    description="Permite sondear el estado del ciclo de vida: solicitado/generando/disponible/error/descargado.",
)
def obtener_reporte(
    id_reporte: int,
    _rol:       str     = Depends(require_roles(*SOLO_ADMIN)),
    db:         Session = Depends(get_db),
) -> ReporteResponse:
    return ReportesService(db).obtener_reporte(id_reporte)


@router.get(
    "/{id_reporte}/descargar",
    summary="RF-18: Descargar el archivo PDF del reporte",
    description=(
        "Retorna el archivo PDF para descarga directa. "
        "Transiciona el reporte a estado 'descargado'. "
        "Diagrama de actividad: 'Mostrar opción de descarga'."
    ),
    response_class=FileResponse,
)
def descargar_reporte(
    id_reporte: int,
    request:    Request,
    usuario_id: int     = Depends(get_current_user_id),
    _rol:       str     = Depends(require_roles(*SOLO_ADMIN)),
    db:         Session = Depends(get_db),
):
    nombre_usuario = request.headers.get("X-Usuario-Nombre", "Administrador")
    return ReportesService(db).descargar_reporte(id_reporte, usuario_id, nombre_usuario)


@router.post(
    "/{id_reporte}/reintentar",
    response_model=ReporteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="RF-18: Reintentar un reporte en estado error",
    description="Diagrama de estados: Error → (reintentar) → Solicitado → Generando → Disponible.",
)
def reintentar_reporte(
    id_reporte: int,
    request:    Request,
    usuario_id: int     = Depends(get_current_user_id),
    _rol:       str     = Depends(require_roles(*SOLO_ADMIN)),
    db:         Session = Depends(get_db),
) -> ReporteResponse:
    nombre_usuario = request.headers.get("X-Usuario-Nombre", "Administrador")
    return ReportesService(db).reintentar_reporte(id_reporte, usuario_id, nombre_usuario)


# ----------------------------------------------------------
# AUDITORÍA
# ----------------------------------------------------------

auditoria_router = APIRouter(prefix="/auditoria", tags=["Reportes y Auditoría"])


@auditoria_router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="RF-18: Registrar evento de auditoría",
    description=(
        "Punto de entrada append-only para que cualquier módulo registre "
        "acciones relevantes. RNF-05: los registros son inmutables una vez creados."
    ),
)
def registrar_auditoria(
    evento:     AuditoriaCreate,
    _rol:       str     = Depends(require_roles(*SOLO_ADMIN)),
    db:         Session = Depends(get_db),
) -> dict:
    id_ev = ReportesService(db).registrar_evento_auditoria(evento)
    return {"id_auditoria": id_ev, "mensaje": "Evento registrado correctamente."}


@auditoria_router.get(
    "",
    summary="RF-18: Consultar log de auditoría",
    description=(
        "Consulta paginada del log de auditoría con filtros por módulo, acción, "
        "resultado, usuario y rango de fechas. Solo Administrador (RN-01, RNF-04)."
    ),
)
def consultar_auditoria(
    modulo:      Optional[str]  = Query(None),
    accion:      Optional[str]  = Query(None),
    resultado:   Optional[str]  = Query(None),
    id_usuario:  Optional[int]  = Query(None),
    fecha_desde: Optional[str]  = Query(None),
    fecha_hasta: Optional[str]  = Query(None),
    page:        int            = Query(1, ge=1),
    page_size:   int            = Query(50, ge=1, le=200),
    _rol:        str            = Depends(require_roles(*SOLO_ADMIN)),
    db:          Session        = Depends(get_db),
) -> dict:
    from datetime import datetime as dt
    filtros = AuditoriaFiltros(
        modulo      = modulo,
        accion      = accion,
        resultado   = resultado,
        id_usuario  = id_usuario,
        fecha_desde = dt.fromisoformat(fecha_desde) if fecha_desde else None,
        fecha_hasta = dt.fromisoformat(fecha_hasta) if fecha_hasta else None,
        page        = page,
        page_size   = page_size,
    )
    registros, total = ReportesService(db).consultar_auditoria(filtros)
    return {
        "total":        total,
        "page":         page,
        "page_size":    page_size,
        "total_pages":  (total + page_size - 1) // page_size,
        "registros":    [r.model_dump() for r in registros],
    }
