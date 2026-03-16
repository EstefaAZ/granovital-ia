# ==============================================================
# modulo_04_ia / app/api/v1/ia.py
# Router FastAPI - Endpoints de Inteligencia Artificial
#
#   RF-05  POST /{cultivo_id}/analisis/enfermedad
#   RF-06  POST /{cultivo_id}/analisis/plaga
#   RF-07  POST /{cultivo_id}/prediccion/fitosanitaria
#   RF-08  POST /{cultivo_id}/recomendacion/riego
#   RF-09  POST /{cultivo_id}/recomendacion/fertilizacion
#          GET  /{cultivo_id}/historial
#          GET  /{cultivo_id}/resumen
#          POST /admin/modelos/{tipo}/reload   (RNF-08)
# ==============================================================

from typing import List, Optional
from fastapi import APIRouter, Depends, Query, UploadFile, File, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user_id, require_roles
from app.ia.motor.clasificador_imagen import ClasificadorImagen
from app.schemas.analisis import (
    AnalisisImagenResponse, HistorialAnalisisResponse,
    PrediccionFitoResponse, RecomendacionRiegoResponse,
    RecomendacionFertResponse, ResumenIAResponse,
)
from app.services.ia_service import IAService

router = APIRouter(prefix="/ia", tags=["Inteligencia Artificial"])

ROLES_CAMPO = ("Caficultor", "Administrador")
ROLES_ADMIN = ("Administrador",)


# ==============================================================
# DASHBOARD CONSOLIDADO
# ==============================================================

@router.get(
    "/{cultivo_id}/resumen",
    response_model=ResumenIAResponse,
    summary="Panel resumen de IA del cultivo",
    description=(
        "Consolida el estado de todos los modelos de IA: "
        "ultimo diagnostico de enfermedades, plagas, riesgo fitosanitario, "
        "recomendaciones de riego y fertilizacion, "
        "estado de validez RN-03 y alertas activas."
    ),
)
def resumen_ia(
    cultivo_id: int,
    usuario_id: int   = Depends(get_current_user_id),
    _rol:       str   = Depends(require_roles(*ROLES_CAMPO)),
    db:         Session = Depends(get_db),
) -> ResumenIAResponse:
    return IAService(db).resumen_ia(cultivo_id, usuario_id)


# ==============================================================
# RF-05 - DETECCION DE ENFERMEDADES
# ==============================================================

@router.post(
    "/{cultivo_id}/analisis/enfermedad",
    response_model=AnalisisImagenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="RF-05: Analizar imagen para detectar enfermedades",
    description=(
        "Analiza una imagen de hoja de cafe mediante modelo CNN. "
        "Detecta: Sano, Roya, Mancha de Hierro, Antracnosis, CBD. "
        "RNF-01: responde en menos de 5 segundos. "
        "CP-05: caso de prueba critico del Test Plan."
    ),
)
async def analizar_enfermedad(
    cultivo_id: int,
    imagen:     UploadFile = File(..., description="Imagen JPG/PNG/WEBP de hoja de cafe"),
    usuario_id: int        = Depends(get_current_user_id),
    _rol:       str        = Depends(require_roles(*ROLES_CAMPO)),
    db:         Session    = Depends(get_db),
) -> AnalisisImagenResponse:
    return await IAService(db).analizar_imagen(cultivo_id, usuario_id, "enfermedad", imagen)


# ==============================================================
# RF-06 - DETECCION DE PLAGAS
# ==============================================================

@router.post(
    "/{cultivo_id}/analisis/plaga",
    response_model=AnalisisImagenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="RF-06: Analizar imagen para detectar plagas",
    description=(
        "Analiza imagen del cultivo para identificar plagas: "
        "Broca del Cafe, Minador de la Hoja, Trips, Acaro Rojo. "
        "RNF-01: responde en menos de 5 segundos."
    ),
)
async def analizar_plaga(
    cultivo_id: int,
    imagen:     UploadFile = File(..., description="Imagen JPG/PNG/WEBP del cultivo"),
    usuario_id: int        = Depends(get_current_user_id),
    _rol:       str        = Depends(require_roles(*ROLES_CAMPO)),
    db:         Session    = Depends(get_db),
) -> AnalisisImagenResponse:
    return await IAService(db).analizar_imagen(cultivo_id, usuario_id, "plaga", imagen)


# ==============================================================
# RF-07 - PREDICCION FITOSANITARIA
# ==============================================================

@router.post(
    "/{cultivo_id}/prediccion/fitosanitaria",
    response_model=PrediccionFitoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="RF-07: Predecir riesgo fitosanitario",
    description=(
        "Predice el nivel de riesgo de enfermedades fungicas "
        "basandose en temperatura, humedad relativa y precipitacion actuales. "
        "RN-03: requiere datos ambientales registrados en las ultimas 24 horas."
    ),
)
def predecir_fitosanitario(
    cultivo_id: int,
    usuario_id: int     = Depends(get_current_user_id),
    _rol:       str     = Depends(require_roles(*ROLES_CAMPO)),
    db:         Session = Depends(get_db),
) -> PrediccionFitoResponse:
    return IAService(db).predecir_fitosanitario(cultivo_id, usuario_id)


# ==============================================================
# RF-08 - RECOMENDACION DE RIEGO
# ==============================================================

@router.post(
    "/{cultivo_id}/recomendacion/riego",
    response_model=RecomendacionRiegoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="RF-08: Recomendar riego automatico",
    description=(
        "Genera recomendacion de riego basada en humedad del suelo, "
        "temperatura y precipitacion reciente. "
        "RN-03: requiere datos de suelo y ambientales de las ultimas 24 horas. "
        "CP-06: caso de prueba del Test Plan."
    ),
)
def recomendar_riego(
    cultivo_id: int,
    usuario_id: int     = Depends(get_current_user_id),
    _rol:       str     = Depends(require_roles(*ROLES_CAMPO)),
    db:         Session = Depends(get_db),
) -> RecomendacionRiegoResponse:
    return IAService(db).recomendar_riego(cultivo_id, usuario_id)


# ==============================================================
# RF-09 - RECOMENDACION DE FERTILIZACION
# ==============================================================

@router.post(
    "/{cultivo_id}/recomendacion/fertilizacion",
    response_model=RecomendacionFertResponse,
    status_code=status.HTTP_201_CREATED,
    summary="RF-09: Recomendar fertilizacion",
    description=(
        "Recomienda tipo, dosis y metodo de fertilizante "
        "segun pH, NPK y materia organica del suelo. "
        "RN-03: requiere datos de suelo de las ultimas 24 horas."
    ),
)
def recomendar_fertilizacion(
    cultivo_id: int,
    usuario_id: int     = Depends(get_current_user_id),
    _rol:       str     = Depends(require_roles(*ROLES_CAMPO)),
    db:         Session = Depends(get_db),
) -> RecomendacionFertResponse:
    return IAService(db).recomendar_fertilizacion(cultivo_id, usuario_id)


# ==============================================================
# CP-07 - HISTORIAL DE ANALISIS
# ==============================================================

@router.get(
    "/{cultivo_id}/historial",
    response_model=List[HistorialAnalisisResponse],
    summary="CP-07: Historial de analisis de IA",
    description=(
        "Retorna el historial de todos los analisis de imagen "
        "realizados sobre el cultivo, ordenados del mas reciente "
        "al mas antiguo. Filtrable por tipo (enfermedad/plaga)."
    ),
)
def historial_analisis(
    cultivo_id: int,
    tipo:       Optional[str] = Query(None, description="'enfermedad' o 'plaga'"),
    limite:     int           = Query(20, ge=1, le=200),
    usuario_id: int           = Depends(get_current_user_id),
    _rol:       str           = Depends(require_roles(*ROLES_CAMPO)),
    db:         Session       = Depends(get_db),
) -> List[HistorialAnalisisResponse]:
    return IAService(db).historial_analisis(cultivo_id, usuario_id, tipo, limite)


# ==============================================================
# RNF-08 - RECARGA DE MODELOS EN CALIENTE
# ==============================================================

@router.post(
    "/admin/modelos/{tipo}/reload",
    summary="RNF-08: Recargar modelo de IA en caliente",
    description=(
        "Permite reemplazar el archivo de modelo en disco "
        "y recargarlo sin reiniciar el servidor. "
        "tipo: 'enfermedad' o 'plaga'. Solo Administrador."
    ),
)
def recargar_modelo(
    tipo: str,
    _rol: str = Depends(require_roles(*ROLES_ADMIN)),
) -> dict:
    if tipo not in ("enfermedad", "plaga"):
        from fastapi import HTTPException
        raise HTTPException(
            status_code=400,
            detail="tipo debe ser 'enfermedad' o 'plaga'",
        )
    clasificador = ClasificadorImagen(tipo)
    clasificador.reload()
    return {
        "mensaje":  f"Modelo '{tipo}' recargado correctamente.",
        "version":  clasificador.version,
        "simulado": clasificador.modo_simulado,
    }
