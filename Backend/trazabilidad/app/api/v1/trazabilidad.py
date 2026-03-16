# ==============================================================
# modulo_05_trazabilidad / app/api/v1/trazabilidad.py
# Router FastAPI — Endpoints de Trazabilidad
#
#   RF-10  CRUD lotes + transiciones de estado
#   RF-11  Control de secado
#   RF-12  Clasificacion del grano
#   RF-15  Consulta publica QR (sin autenticacion - RN-05)
#
# Roles por endpoint:
#   Productor     -> gestiona sus propios lotes
#   Administrador -> acceso total + correcciones RN-04
#   Publico       -> solo GET /publico/{codigo} (RN-05)
# ==============================================================

from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import (
    get_current_user_id, get_current_user_rol, require_roles,
)
from app.schemas.trazabilidad import (
    ClasificacionCreate, ClasificacionResponse,
    EventoResponse, LoteCreate, LotePublicoResponse,
    LoteResponse, LoteUpdate, ResumenSecadoResponse,
    SecadoCreate, SecadoResponse, TransicionEstadoResponse,
)
from app.services.trazabilidad_service import TrazabilidadService

router = APIRouter(prefix="/trazabilidad", tags=["Trazabilidad"])

ROLES_PRODUCTOR = ("Productor", "Administrador")
ROLES_ADMIN     = ("Administrador",)


# ==============================================================
# RF-10 — GESTION DE LOTES
# ==============================================================

@router.post(
    "/lotes",
    response_model=LoteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="RF-10 / CP-04: Registrar nuevo lote de cafe",
    description=(
        "Crea un lote de cafe asignandolo al cultivo indicado. "
        "Estado inicial: 'registrado' (Diagrama de Estados LOTE). "
        "RN-02: el lote debe completar trazabilidad antes de venderse."
    ),
)
def crear_lote(
    datos:      LoteCreate,
    usuario_id: int     = Depends(get_current_user_id),
    _rol:       str     = Depends(require_roles(*ROLES_PRODUCTOR)),
    db:         Session = Depends(get_db),
) -> LoteResponse:
    return TrazabilidadService(db).crear_lote(datos, usuario_id)


@router.get(
    "/lotes",
    response_model=List[LoteResponse],
    summary="RF-10: Listar lotes del usuario",
)
def listar_lotes(
    cultivo_id: Optional[int] = Query(None, description="Filtrar por cultivo"),
    usuario_id: int     = Depends(get_current_user_id),
    _rol:       str     = Depends(require_roles(*ROLES_PRODUCTOR)),
    db:         Session = Depends(get_db),
) -> List[LoteResponse]:
    return TrazabilidadService(db).listar_lotes(usuario_id, cultivo_id)


@router.get(
    "/lotes/{id_lote}",
    response_model=LoteResponse,
    summary="RF-10: Obtener detalle de un lote",
)
def obtener_lote(
    id_lote:    int,
    usuario_id: int     = Depends(get_current_user_id),
    _rol:       str     = Depends(require_roles(*ROLES_PRODUCTOR)),
    db:         Session = Depends(get_db),
) -> LoteResponse:
    return TrazabilidadService(db).obtener_lote(id_lote, usuario_id)


@router.patch(
    "/lotes/{id_lote}",
    response_model=LoteResponse,
    summary="RF-10 / RN-04: Actualizar datos del lote",
    description=(
        "Actualiza campos operativos del lote. "
        "RN-04: bloqueado para lotes validados (aprobado/vendido) "
        "si el solicitante no es Administrador."
    ),
)
def actualizar_lote(
    id_lote:    int,
    datos:      LoteUpdate,
    usuario_id: int     = Depends(get_current_user_id),
    rol:        str     = Depends(require_roles(*ROLES_PRODUCTOR)),
    db:         Session = Depends(get_db),
) -> LoteResponse:
    es_admin = rol == "Administrador"
    return TrazabilidadService(db).actualizar_lote(id_lote, datos, usuario_id, es_admin)


@router.post(
    "/lotes/{id_lote}/confirmar",
    response_model=TransicionEstadoResponse,
    summary="RF-10: Confirmar lote (Registrado → Disponible)",
    description=(
        "Transicion del Diagrama de Estados: confirmarRegistro. "
        "El lote pasa de 'registrado' a 'disponible', "
        "habilitando el inicio del proceso de secado."
    ),
)
def confirmar_lote(
    id_lote:    int,
    usuario_id: int     = Depends(get_current_user_id),
    _rol:       str     = Depends(require_roles(*ROLES_PRODUCTOR)),
    db:         Session = Depends(get_db),
) -> TransicionEstadoResponse:
    return TrazabilidadService(db).confirmar_lote(id_lote, usuario_id)


@router.post(
    "/lotes/{id_lote}/venta",
    response_model=TransicionEstadoResponse,
    summary="RF-10 / RN-02: Registrar venta del lote (Aprobado → Vendido)",
    description=(
        "Registra la venta del lote. "
        "RN-02: solo lotes en estado 'aprobado' con clasificacion "
        "de calidad completa pueden ser comercializados."
    ),
)
def registrar_venta(
    id_lote:    int,
    comprador:  str     = Query(..., description="Nombre del comprador"),
    precio_kg:  float   = Query(..., description="Precio por kg en COP"),
    destino:    Optional[str] = Query(None, description="Pais o ciudad de destino"),
    usuario_id: int     = Depends(get_current_user_id),
    _rol:       str     = Depends(require_roles(*ROLES_PRODUCTOR)),
    db:         Session = Depends(get_db),
) -> TransicionEstadoResponse:
    return TrazabilidadService(db).registrar_venta(
        id_lote, usuario_id, comprador, precio_kg, destino
    )


@router.get(
    "/lotes/{id_lote}/eventos",
    response_model=List[EventoResponse],
    summary="RF-10 / RN-04: Log de eventos del lote",
    description=(
        "Retorna el historial cronologico e inmutable de todos "
        "los eventos del ciclo de vida del lote. "
        "Implementa trazabilidad completa requerida por RN-04."
    ),
)
def log_eventos(
    id_lote:    int,
    usuario_id: int     = Depends(get_current_user_id),
    _rol:       str     = Depends(require_roles(*ROLES_PRODUCTOR)),
    db:         Session = Depends(get_db),
) -> List[EventoResponse]:
    return TrazabilidadService(db).log_eventos(id_lote, usuario_id)


# ==============================================================
# RF-11 — CONTROL DE SECADO
# ==============================================================

@router.post(
    "/lotes/{id_lote}/secado",
    response_model=SecadoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="RF-11: Registrar lectura de secado",
    description=(
        "Registra temperatura y humedad durante el proceso de secado. "
        "Calcula alertas segun umbrales CENICAFE (35-45 C optimo). "
        "Detecta automaticamente cuando el proceso se completa "
        "(humedad <= 11% y horas >= 72)."
    ),
)
def registrar_secado(
    id_lote:    int,
    datos:      SecadoCreate,
    usuario_id: int     = Depends(get_current_user_id),
    _rol:       str     = Depends(require_roles(*ROLES_PRODUCTOR)),
    db:         Session = Depends(get_db),
) -> SecadoResponse:
    return TrazabilidadService(db).registrar_lectura_secado(id_lote, datos, usuario_id)


@router.get(
    "/lotes/{id_lote}/secado/resumen",
    response_model=ResumenSecadoResponse,
    summary="RF-11: Resumen del proceso de secado",
    description=(
        "Muestra el estado actual del secado: temperatura promedio, "
        "humedad actual, horas acumuladas, progreso hacia el objetivo "
        "del 11% y alertas activas."
    ),
)
def resumen_secado(
    id_lote:    int,
    usuario_id: int     = Depends(get_current_user_id),
    _rol:       str     = Depends(require_roles(*ROLES_PRODUCTOR)),
    db:         Session = Depends(get_db),
) -> ResumenSecadoResponse:
    return TrazabilidadService(db).resumen_secado(id_lote, usuario_id)


# ==============================================================
# RF-12 — CLASIFICACION DEL GRANO
# ==============================================================

@router.post(
    "/lotes/{id_lote}/clasificacion",
    response_model=ClasificacionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="RF-12: Clasificar grano por calidad",
    description=(
        "Clasifica el grano segun la norma FNC (Supremo, Excelso Extra, "
        "Excelso, Corriente, Pasilla) usando numero de defectos y humedad. "
        "Genera transicion de estado: 'aprobado' o 'con_problema'. "
        "Calcula hash de integridad (RN-04) y activa el QR publico (RN-05)."
    ),
)
def clasificar_grano(
    id_lote:    int,
    datos:      ClasificacionCreate,
    usuario_id: int     = Depends(get_current_user_id),
    _rol:       str     = Depends(require_roles(*ROLES_PRODUCTOR)),
    db:         Session = Depends(get_db),
) -> ClasificacionResponse:
    return TrazabilidadService(db).clasificar_grano(id_lote, datos, usuario_id)


# ==============================================================
# RF-15 / RN-05 — CONSULTA PUBLICA (SIN AUTENTICACION)
# ==============================================================

@router.get(
    "/publico/{codigo_lote}",
    response_model=LotePublicoResponse,
    summary="RF-15 / RN-05: Consulta publica del lote via QR",
    description=(
        "Endpoint publico para el consumidor. No requiere autenticacion. "
        "RN-05: solo expone informacion de trazabilidad y calidad, "
        "nunca datos internos como precios de compra, IDs de sistema "
        "o informacion de usuarios. "
        "El consumidor accede escaneando el codigo QR del empaque."
    ),
    tags=["Consulta Publica"],
)
def consulta_publica(
    codigo_lote: str,
    db:          Session = Depends(get_db),
) -> LotePublicoResponse:
    return TrazabilidadService(db).consulta_publica(codigo_lote)
