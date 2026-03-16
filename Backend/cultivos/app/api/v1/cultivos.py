# ==============================================================
# modulo_02_cultivos / app/api/v1/cultivos.py
# Router FastAPI - Endpoints de Cultivos, Lotes y Sensores
#
# Trazabilidad de requisitos:
#   RF-03  Gestion de cultivos (CRUD completo)
#   RF-04  Registro de lotes
#   RF-15  Generacion de QR al crear lote
#   RN-01  RBAC por rol
#   RN-02  Validacion de trazabilidad antes de vender
#   RNF-01 Respuesta en menos de 5 segundos
#   RNF-02 Usabilidad - mensajes claros en espanol
# ==============================================================

from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user_id, require_roles
from app.schemas.cultivo import (
    CultivoCreate, CultivoUpdate, CultivoResponse,
    LoteCreate, LoteUpdate, LoteResponse,
    SensorCreate, SensorResponse,
    ResumenCultivoResponse,
)
from app.services.cultivo_service import CultivoService

router = APIRouter(prefix="/cultivos", tags=["Gestion de Cultivos y Lotes"])

# Roles autorizados segun RN-01
ROLES_CAFICULTOR  = ("Caficultor", "Administrador")
ROLES_PRODUCTOR   = ("Productor", "Caficultor", "Administrador")
ROLES_SOLO_ADMIN  = ("Administrador",)


# ==============================================================
# DASHBOARD DEL CAFICULTOR
# ==============================================================

@router.get(
    "/resumen",
    response_model=ResumenCultivoResponse,
    summary="Resumen del panel principal",
    description=(
        "Retorna estadisticas consolidadas del caficultor: "
        "cultivos activos, total de lotes, area total y estado de lotes."
    ),
)
def resumen_dashboard(
    usuario_id: int     = Depends(get_current_user_id),
    _rol: str           = Depends(require_roles(*ROLES_CAFICULTOR)),
    db:   Session       = Depends(get_db),
) -> ResumenCultivoResponse:
    return CultivoService(db).resumen_dashboard(usuario_id)


# ==============================================================
# CULTIVOS - RF-03
# ==============================================================

@router.post(
    "",
    response_model=CultivoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar cultivo",
    description=(
        "RF-03: registra un nuevo cultivo en estado 'creado'. "
        "El cultivo queda vinculado al Caficultor autenticado."
    ),
)
def crear_cultivo(
    datos:      CultivoCreate,
    usuario_id: int     = Depends(get_current_user_id),
    _rol: str           = Depends(require_roles(*ROLES_CAFICULTOR)),
    db:   Session       = Depends(get_db),
) -> CultivoResponse:
    cultivo  = CultivoService(db).crear_cultivo(datos, usuario_id)
    total_l  = len(cultivo.lotes) if cultivo.lotes else 0
    total_s  = len(cultivo.sensores) if cultivo.sensores else 0
    return CultivoResponse(
        **{c.name: getattr(cultivo, c.name) for c in cultivo.__table__.columns},
        total_lotes=total_l,
        total_sensores=total_s,
    )


@router.get(
    "",
    response_model=List[CultivoResponse],
    summary="Listar mis cultivos",
    description=(
        "Retorna todos los cultivos activos del Caficultor autenticado. "
        "No incluye cultivos eliminados."
    ),
)
def listar_cultivos(
    usuario_id: int     = Depends(get_current_user_id),
    _rol: str           = Depends(require_roles(*ROLES_CAFICULTOR)),
    db:   Session       = Depends(get_db),
) -> List[CultivoResponse]:
    cultivos = CultivoService(db).listar_cultivos(usuario_id)
    return [
        CultivoResponse(
            **{c.name: getattr(cultivo, c.name) for c in cultivo.__table__.columns},
            total_lotes=len(cultivo.lotes),
            total_sensores=len(cultivo.sensores),
        )
        for cultivo in cultivos
    ]


@router.get(
    "/{cultivo_id}",
    response_model=CultivoResponse,
    summary="Consultar cultivo por ID",
)
def obtener_cultivo(
    cultivo_id: int,
    usuario_id: int     = Depends(get_current_user_id),
    _rol: str           = Depends(require_roles(*ROLES_CAFICULTOR)),
    db:   Session       = Depends(get_db),
) -> CultivoResponse:
    cultivo = CultivoService(db).obtener_cultivo(cultivo_id, usuario_id)
    return CultivoResponse(
        **{c.name: getattr(cultivo, c.name) for c in cultivo.__table__.columns},
        total_lotes=len(cultivo.lotes),
        total_sensores=len(cultivo.sensores),
    )


@router.patch(
    "/{cultivo_id}",
    response_model=CultivoResponse,
    summary="Actualizar cultivo",
    description=(
        "Actualiza los datos del cultivo. "
        "Si incluye un cambio de estado, valida la transicion "
        "segun el diagrama de estados oficial del proyecto."
    ),
)
def actualizar_cultivo(
    cultivo_id: int,
    datos:      CultivoUpdate,
    usuario_id: int     = Depends(get_current_user_id),
    _rol: str           = Depends(require_roles(*ROLES_CAFICULTOR)),
    db:   Session       = Depends(get_db),
) -> CultivoResponse:
    cultivo = CultivoService(db).actualizar_cultivo(cultivo_id, datos, usuario_id)
    return CultivoResponse(
        **{c.name: getattr(cultivo, c.name) for c in cultivo.__table__.columns},
        total_lotes=len(cultivo.lotes),
        total_sensores=len(cultivo.sensores),
    )


@router.delete(
    "/{cultivo_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar cultivo",
    description="Eliminacion logica. El cultivo pasa a estado 'eliminado'.",
)
def eliminar_cultivo(
    cultivo_id: int,
    usuario_id: int     = Depends(get_current_user_id),
    _rol: str           = Depends(require_roles(*ROLES_CAFICULTOR)),
    db:   Session       = Depends(get_db),
) -> None:
    CultivoService(db).eliminar_cultivo(cultivo_id, usuario_id)


# ==============================================================
# LOTES - RF-04
# ==============================================================

@router.post(
    "/{cultivo_id}/lotes",
    response_model=LoteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar lote de produccion",
    description=(
        "RF-04: registra un nuevo lote vinculado al cultivo. "
        "Genera automaticamente un codigo QR unico para el lote (RF-15). "
        "El lote comienza en estado 'registrado'."
    ),
)
def crear_lote(
    cultivo_id: int,
    datos:      LoteCreate,
    usuario_id: int     = Depends(get_current_user_id),
    _rol: str           = Depends(require_roles(*ROLES_PRODUCTOR)),
    db:   Session       = Depends(get_db),
) -> LoteResponse:
    return CultivoService(db).crear_lote(cultivo_id, datos, usuario_id)


@router.get(
    "/{cultivo_id}/lotes",
    response_model=List[LoteResponse],
    summary="Listar lotes del cultivo",
)
def listar_lotes(
    cultivo_id: int,
    usuario_id: int     = Depends(get_current_user_id),
    _rol: str           = Depends(require_roles(*ROLES_PRODUCTOR)),
    db:   Session       = Depends(get_db),
) -> List[LoteResponse]:
    return CultivoService(db).listar_lotes(cultivo_id, usuario_id)


@router.get(
    "/{cultivo_id}/lotes/{lote_id}",
    response_model=LoteResponse,
    summary="Consultar lote por ID",
)
def obtener_lote(
    cultivo_id: int,
    lote_id:    int,
    usuario_id: int     = Depends(get_current_user_id),
    _rol: str           = Depends(require_roles(*ROLES_PRODUCTOR)),
    db:   Session       = Depends(get_db),
) -> LoteResponse:
    return CultivoService(db).obtener_lote(lote_id, usuario_id)


@router.patch(
    "/{cultivo_id}/lotes/{lote_id}",
    response_model=LoteResponse,
    summary="Actualizar estado del lote",
    description=(
        "Actualiza el estado u observaciones de un lote. "
        "RN-02: si el nuevo estado es 'vendido', el sistema verifica "
        "que exista la etapa 'comercializacion' en Trazabilidad."
    ),
)
def actualizar_lote(
    cultivo_id: int,
    lote_id:    int,
    datos:      LoteUpdate,
    usuario_id: int     = Depends(get_current_user_id),
    _rol: str           = Depends(require_roles(*ROLES_PRODUCTOR)),
    db:   Session       = Depends(get_db),
) -> LoteResponse:
    return CultivoService(db).actualizar_lote(lote_id, datos, usuario_id)


@router.delete(
    "/{cultivo_id}/lotes/{lote_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar lote",
    description="Eliminacion logica. El lote pasa a estado 'eliminado'.",
)
def eliminar_lote(
    cultivo_id: int,
    lote_id:    int,
    usuario_id: int     = Depends(get_current_user_id),
    _rol: str           = Depends(require_roles(*ROLES_PRODUCTOR)),
    db:   Session       = Depends(get_db),
) -> None:
    CultivoService(db).eliminar_lote(lote_id, usuario_id)


# ==============================================================
# SENSORES - RNF-06, RNF-09
# ==============================================================

@router.post(
    "/{cultivo_id}/sensores",
    response_model=SensorResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar sensor IoT",
    description=(
        "RNF-06: registra un nuevo sensor IoT en el cultivo. "
        "Solo el Administrador puede realizar esta operacion."
    ),
)
def registrar_sensor(
    cultivo_id: int,
    datos:      SensorCreate,
    usuario_id: int     = Depends(get_current_user_id),
    _rol: str           = Depends(require_roles(*ROLES_SOLO_ADMIN)),
    db:   Session       = Depends(get_db),
) -> SensorResponse:
    return CultivoService(db).registrar_sensor(cultivo_id, datos, usuario_id)


@router.get(
    "/{cultivo_id}/sensores",
    response_model=List[SensorResponse],
    summary="Listar sensores del cultivo",
)
def listar_sensores(
    cultivo_id: int,
    usuario_id: int     = Depends(get_current_user_id),
    _rol: str           = Depends(require_roles(*ROLES_CAFICULTOR)),
    db:   Session       = Depends(get_db),
) -> List[SensorResponse]:
    return CultivoService(db).listar_sensores(cultivo_id, usuario_id)
