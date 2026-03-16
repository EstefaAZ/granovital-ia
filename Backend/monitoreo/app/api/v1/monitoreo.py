# ==============================================================
# modulo_03_monitoreo / app/api/v1/monitoreo.py
# Router FastAPI - Endpoints de Monitoreo Ambiental y Suelo
#
# Trazabilidad de requisitos:
#   RF-03  Registrar y consultar variables ambientales
#   RF-04  Registrar y consultar estado del suelo
#   RN-01  RBAC - solo Caficultor y Administrador
#   RN-03  Endpoint de validez consultado por Modulo 04
#   RNF-01 Respuesta en menos de 5 segundos
#   RNF-02 Mensajes en espanol para usuarios no tecnicos
#   RNF-10 Soporte de ingreso manual para zonas rurales
# ==============================================================

from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user_id, require_roles
from app.schemas.monitoreo import (
    MonitoreoAmbientalCreate, MonitoreoAmbientalResponse,
    MonitoreoSueloCreate, MonitoreoSueloResponse,
    ValidezDatosResponse, ResumenMonitoreoResponse,
)
from app.services.monitoreo_service import MonitoreoService

router = APIRouter(prefix="/monitoreo", tags=["Monitoreo Ambiental y Suelo"])

ROLES_CAMPO = ("Caficultor", "Administrador")


# ==============================================================
# DASHBOARD - RESUMEN CONSOLIDADO
# ==============================================================

@router.get(
    "/{cultivo_id}/resumen",
    response_model=ResumenMonitoreoResponse,
    summary="Resumen de monitoreo del cultivo",
    description=(
        "Consolida la ultima lectura ambiental, la ultima lectura "
        "de suelo, el estado de validez RN-03 y las alertas activas "
        "en una sola respuesta para el panel del Caficultor."
    ),
)
def resumen_monitoreo(
    cultivo_id: int,
    usuario_id: int     = Depends(get_current_user_id),
    _rol: str           = Depends(require_roles(*ROLES_CAMPO)),
    db:   Session       = Depends(get_db),
) -> ResumenMonitoreoResponse:
    return MonitoreoService(db).resumen_monitoreo(cultivo_id, usuario_id)


# ==============================================================
# RF-03 - MONITOREO AMBIENTAL
# ==============================================================

@router.post(
    "/{cultivo_id}/ambiental",
    response_model=MonitoreoAmbientalResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar lectura ambiental",
    description=(
        "RF-03: registra temperatura, humedad relativa, precipitacion, "
        "radiacion solar y velocidad del viento. "
        "Acepta origen: sensor_iot, manual o api_externa. "
        "RNF-10: el origen 'manual' permite operar sin conectividad IoT."
    ),
)
def registrar_ambiental(
    cultivo_id: int,
    datos:      MonitoreoAmbientalCreate,
    usuario_id: int     = Depends(get_current_user_id),
    _rol: str           = Depends(require_roles(*ROLES_CAMPO)),
    db:   Session       = Depends(get_db),
) -> MonitoreoAmbientalResponse:
    return MonitoreoService(db).registrar_ambiental(cultivo_id, datos, usuario_id)


@router.get(
    "/{cultivo_id}/ambiental",
    response_model=List[MonitoreoAmbientalResponse],
    summary="Historial de lecturas ambientales",
    description=(
        "RF-03: retorna el historial de lecturas ambientales del cultivo "
        "ordenado de mas reciente a mas antiguo. Maximo 500 registros."
    ),
)
def listar_ambiental(
    cultivo_id: int,
    limite:     int     = Query(50, ge=1, le=500, description="Numero de registros a retornar"),
    usuario_id: int     = Depends(get_current_user_id),
    _rol: str           = Depends(require_roles(*ROLES_CAMPO)),
    db:   Session       = Depends(get_db),
) -> List[MonitoreoAmbientalResponse]:
    return MonitoreoService(db).listar_ambiental(cultivo_id, usuario_id, limite)


@router.get(
    "/{cultivo_id}/ambiental/ultima",
    response_model=Optional[MonitoreoAmbientalResponse],
    summary="Ultima lectura ambiental",
    description=(
        "Retorna unicamente la lectura ambiental mas reciente del cultivo. "
        "Util para el panel en tiempo real."
    ),
)
def ultima_ambiental(
    cultivo_id: int,
    usuario_id: int     = Depends(get_current_user_id),
    _rol: str           = Depends(require_roles(*ROLES_CAMPO)),
    db:   Session       = Depends(get_db),
) -> Optional[MonitoreoAmbientalResponse]:
    return MonitoreoService(db).ultima_lectura_ambiental(cultivo_id, usuario_id)


# ==============================================================
# RF-04 - MONITOREO DE SUELO
# ==============================================================

@router.post(
    "/{cultivo_id}/suelo",
    response_model=MonitoreoSueloResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar lectura de suelo",
    description=(
        "RF-04: registra pH, humedad, nitrogeno, fosforo, potasio, "
        "materia organica y conductividad electrica del suelo. "
        "Acepta origen: sensor_iot, laboratorio o manual. "
        "Calcula interpretacion del pH y alertas de deficiencia nutricional."
    ),
)
def registrar_suelo(
    cultivo_id: int,
    datos:      MonitoreoSueloCreate,
    usuario_id: int     = Depends(get_current_user_id),
    _rol: str           = Depends(require_roles(*ROLES_CAMPO)),
    db:   Session       = Depends(get_db),
) -> MonitoreoSueloResponse:
    return MonitoreoService(db).registrar_suelo(cultivo_id, datos, usuario_id)


@router.get(
    "/{cultivo_id}/suelo",
    response_model=List[MonitoreoSueloResponse],
    summary="Historial de lecturas de suelo",
    description=(
        "RF-04: retorna el historial de lecturas de suelo del cultivo "
        "ordenado de mas reciente a mas antiguo. Maximo 500 registros."
    ),
)
def listar_suelo(
    cultivo_id: int,
    limite:     int     = Query(50, ge=1, le=500, description="Numero de registros a retornar"),
    usuario_id: int     = Depends(get_current_user_id),
    _rol: str           = Depends(require_roles(*ROLES_CAMPO)),
    db:   Session       = Depends(get_db),
) -> List[MonitoreoSueloResponse]:
    return MonitoreoService(db).listar_suelo(cultivo_id, usuario_id, limite)


@router.get(
    "/{cultivo_id}/suelo/ultima",
    response_model=Optional[MonitoreoSueloResponse],
    summary="Ultima lectura de suelo",
    description="Retorna unicamente la lectura de suelo mas reciente del cultivo.",
)
def ultima_suelo(
    cultivo_id: int,
    usuario_id: int     = Depends(get_current_user_id),
    _rol: str           = Depends(require_roles(*ROLES_CAMPO)),
    db:   Session       = Depends(get_db),
) -> Optional[MonitoreoSueloResponse]:
    return MonitoreoService(db).ultima_lectura_suelo(cultivo_id, usuario_id)


# ==============================================================
# RN-03 - VALIDACION DE DATOS ACTUALIZADOS
# ==============================================================

@router.get(
    "/{cultivo_id}/validez",
    response_model=ValidezDatosResponse,
    summary="Verificar validez de datos para IA (RN-03)",
    description=(
        "RN-03: verifica si los datos ambientales y de suelo estan "
        "dentro del umbral de frescura configurado (24 horas por defecto). "
        "El Modulo 04 de IA consulta este endpoint antes de generar "
        "cualquier recomendacion automatica de riego o fertilizacion. "
        "Si ambos_validos=false el sistema no puede recomendar."
    ),
)
def verificar_validez(
    cultivo_id: int,
    usuario_id: int     = Depends(get_current_user_id),
    _rol: str           = Depends(require_roles(*ROLES_CAMPO)),
    db:   Session       = Depends(get_db),
) -> ValidezDatosResponse:
    return MonitoreoService(db).verificar_validez_rn03(cultivo_id, usuario_id)
