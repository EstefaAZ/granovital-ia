# ==============================================================
# modulo_06_mercado / app/api/v1/mercado.py
# Router FastAPI — RF-13 (precios) y RF-14 (demanda)
#
# Endpoints:
#   GET  /mercado/dashboard              Panel consolidado
#   POST /mercado/precios                Registrar precio manual
#   GET  /mercado/precios                Listar histórico
#   POST /mercado/precios/sincronizar    Importar desde M05
#   GET  /mercado/precios/historial      Serie mensual para gráficas
#   POST /mercado/precios/analisis       Ejecutar análisis RF-13
#   POST /mercado/demanda/analisis       Ejecutar análisis RF-14
#
# Roles autorizados: Comercializador, Administrador (RN-01)
# ==============================================================

from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user_id, require_roles
from app.schemas.mercado import (
    AnalisisDemandaResponse,
    AnalisisPrecioResponse,
    DashboardMercadoResponse,
    DemandaObservacionCreate,
    HistorialPrecioItem,
    PrecioCreate,
    PrecioResponse,
)
from app.services.mercado_service import MercadoService

router = APIRouter(prefix="/mercado", tags=["Mercado"])
ROLES = ("Comercializador", "Administrador")


@router.get(
    "/dashboard",
    response_model=DashboardMercadoResponse,
    summary="RF-13 + RF-14: Dashboard consolidado del Comercializador",
    description=(
        "Panel que consolida precio actual, stock disponible (M05), "
        "ventas del mes, nivel de demanda, proyección de precio y alertas. "
        "Diseñado para apoyar decisiones comerciales (RNF-02)."
    ),
)
def dashboard_mercado(
    usuario_id: int     = Depends(get_current_user_id),
    _rol:       str     = Depends(require_roles(*ROLES)),
    db:         Session = Depends(get_db),
) -> DashboardMercadoResponse:
    return MercadoService(db).dashboard_mercado(usuario_id)


@router.post(
    "/precios",
    response_model=PrecioResponse,
    status_code=status.HTTP_201_CREATED,
    summary="RF-13: Registrar precio de referencia de mercado",
    description=(
        "Permite al Comercializador ingresar precios de referencia externos: "
        "precio FNC, bolsa de New York (contrato C), o precios locales. "
        "Se complementa con los precios propios importados automáticamente del M05."
    ),
)
def registrar_precio(
    datos:      PrecioCreate,
    usuario_id: int     = Depends(get_current_user_id),
    _rol:       str     = Depends(require_roles(*ROLES)),
    db:         Session = Depends(get_db),
) -> PrecioResponse:
    return MercadoService(db).registrar_precio(datos, usuario_id)


@router.get(
    "/precios",
    response_model=List[PrecioResponse],
    summary="RF-13: Listar histórico de precios",
)
def listar_precios(
    fuente:     Optional[str] = Query(None, description="Filtrar por fuente: fnc, bolsa_ny, propio_sistema..."),
    meses:      int           = Query(6, ge=1, le=24, description="Meses hacia atrás a listar"),
    usuario_id: int     = Depends(get_current_user_id),
    _rol:       str     = Depends(require_roles(*ROLES)),
    db:         Session = Depends(get_db),
) -> List[PrecioResponse]:
    return MercadoService(db).listar_precios(usuario_id, fuente, meses)


@router.post(
    "/precios/sincronizar",
    summary="RF-13: Importar precios de ventas propias desde M05",
    description=(
        "Sincroniza automáticamente los precios de venta reales de los lotes "
        "vendidos en el Módulo 05 (trazabilidad) hacia el histórico de precios. "
        "Retorna la cantidad de registros nuevos importados."
    ),
)
def sincronizar_ventas(
    usuario_id: int     = Depends(get_current_user_id),
    _rol:       str     = Depends(require_roles(*ROLES)),
    db:         Session = Depends(get_db),
) -> dict:
    importados = MercadoService(db).sincronizar_ventas_propias(usuario_id)
    return {
        "importados": importados,
        "mensaje": (
            f"{importados} precio(s) de ventas propias importados correctamente."
            if importados else
            "No hay ventas nuevas pendientes de sincronizar."
        ),
    }


@router.get(
    "/precios/historial",
    response_model=List[HistorialPrecioItem],
    summary="RF-13: Histórico mensual de precios para gráficas",
    description=(
        "Retorna la serie temporal mensual de precios agrupada por fuente "
        "(FNC, propio sistema). Usada por el dashboard para graficar tendencias."
    ),
)
def historial_precios(
    meses:     int = Query(6, ge=1, le=24),
    tipo_cafe: str = Query("pergamino_seco"),
    _rol:      str = Depends(require_roles(*ROLES)),
    db:        Session = Depends(get_db),
) -> List[HistorialPrecioItem]:
    return MercadoService(db).historial_precios(meses, tipo_cafe)


@router.post(
    "/precios/analisis",
    response_model=AnalisisPrecioResponse,
    status_code=status.HTTP_201_CREATED,
    summary="RF-13: Ejecutar análisis estadístico de precios",
    description=(
        "Calcula media, mínimo, máximo, variación porcentual y proyección "
        "WMA-3 del período. Clasifica la tendencia (alza/baja/estable/volátil) "
        "y genera alertas y recomendaciones comerciales en lenguaje claro (RNF-02)."
    ),
)
def analizar_precios(
    meses:         int = Query(
        6, ge=1, le=24,
        description="Meses del período a analizar (default: 6)"
    ),
    tipo_cafe:     str = Query("pergamino_seco"),
    fuente_filtro: str = Query(
        "todas",
        description="Fuente de datos: todas, fnc, propio_sistema, mercado_local..."
    ),
    usuario_id:    int     = Depends(get_current_user_id),
    _rol:          str     = Depends(require_roles(*ROLES)),
    db:            Session = Depends(get_db),
) -> AnalisisPrecioResponse:
    return MercadoService(db).analizar_precios(
        usuario_id, meses, tipo_cafe, fuente_filtro
    )


@router.post(
    "/demanda/analisis",
    response_model=AnalisisDemandaResponse,
    status_code=status.HTTP_201_CREATED,
    summary="RF-14: Ejecutar análisis de demanda del mercado",
    description=(
        "Analiza la demanda a partir de lotes vendidos en M05: volumen, "
        "velocidad de venta, categorías demandadas, compradores frecuentes "
        "y destinos. Clasifica el nivel de demanda (baja/media/alta/muy_alta) "
        "y genera recomendaciones comerciales en lenguaje accesible (RNF-02). "
        "El cuerpo de la petición es opcional y permite agregar observaciones "
        "de mercado externas (ferias, pedidos anticipados, tendencias)."
    ),
)
def analizar_demanda(
    meses:         int = Query(6, ge=1, le=24),
    observaciones: Optional[DemandaObservacionCreate] = None,
    usuario_id:    int     = Depends(get_current_user_id),
    _rol:          str     = Depends(require_roles(*ROLES)),
    db:            Session = Depends(get_db),
) -> AnalisisDemandaResponse:
    return MercadoService(db).analizar_demanda(usuario_id, meses, observaciones)
