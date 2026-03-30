from fastapi import APIRouter, Request
from fastapi.responses import Response
from app.core.config import settings
from app.services.proxy import reenviar_peticion

router = APIRouter()

def _ruta(base_url: str, path_suffix: str) -> str:
    return f"{base_url.rstrip('/')}{path_suffix}"

# ── Auth ──────────────────────────────────────────────────────
@router.api_route("/api/v1/auth/{ruta:path}", methods=["GET","POST","PUT","PATCH","DELETE","OPTIONS"], tags=["Auth"])
async def proxy_auth(request: Request, ruta: str) -> Response:
    return await reenviar_peticion(request, _ruta(settings.URL_AUTH, f"/api/v1/auth/{ruta}"))

# ── Cultivos ──────────────────────────────────────────────────
@router.api_route("/api/v1/cultivos", methods=["GET","POST","OPTIONS"], tags=["Cultivos"])
async def proxy_cultivos_raiz(request: Request) -> Response:
    return await reenviar_peticion(request, _ruta(settings.URL_CULTIVOS, "/api/v1/cultivos"))

@router.api_route("/api/v1/cultivos/{ruta:path}", methods=["GET","POST","PUT","PATCH","DELETE","OPTIONS"], tags=["Cultivos"])
async def proxy_cultivos(request: Request, ruta: str) -> Response:
    return await reenviar_peticion(request, _ruta(settings.URL_CULTIVOS, f"/api/v1/cultivos/{ruta}"))

# ── Monitoreo ─────────────────────────────────────────────────
@router.api_route("/api/v1/monitoreo/{ruta:path}", methods=["GET","POST","PUT","PATCH","DELETE","OPTIONS"], tags=["Monitoreo"])
async def proxy_monitoreo(request: Request, ruta: str) -> Response:
    return await reenviar_peticion(request, _ruta(settings.URL_MONITOREO, f"/api/v1/monitoreo/{ruta}"))

# ── IA ────────────────────────────────────────────────────────
@router.api_route("/api/v1/ia/{ruta:path}", methods=["GET","POST","PUT","PATCH","DELETE","OPTIONS"], tags=["IA"])
async def proxy_ia(request: Request, ruta: str) -> Response:
    return await reenviar_peticion(request, _ruta(settings.URL_IA, f"/api/v1/ia/{ruta}"))

# ── Trazabilidad ──────────────────────────────────────────────
@router.api_route("/api/v1/trazabilidad/{ruta:path}", methods=["GET","POST","PUT","PATCH","DELETE","OPTIONS"], tags=["Trazabilidad"])
async def proxy_trazabilidad(request: Request, ruta: str) -> Response:
    return await reenviar_peticion(request, _ruta(settings.URL_TRAZABILIDAD, f"/api/v1/trazabilidad/{ruta}"))

# ── Mercado ───────────────────────────────────────────────────
@router.api_route("/api/v1/mercado", methods=["GET","POST","OPTIONS"], tags=["Mercado"])
async def proxy_mercado_raiz(request: Request) -> Response:
    return await reenviar_peticion(request, _ruta(settings.URL_MERCADO, "/api/v1/mercado"))

@router.api_route("/api/v1/mercado/{ruta:path}", methods=["GET","POST","PUT","PATCH","DELETE","OPTIONS"], tags=["Mercado"])
async def proxy_mercado(request: Request, ruta: str) -> Response:
    return await reenviar_peticion(request, _ruta(settings.URL_MERCADO, f"/api/v1/mercado/{ruta}"))

# ── Reportes ──────────────────────────────────────────────────
@router.api_route("/api/v1/reportes", methods=["GET","POST","OPTIONS"], tags=["Reportes"])
async def proxy_reportes_raiz(request: Request) -> Response:
    return await reenviar_peticion(request, _ruta(settings.URL_REPORTES, "/api/v1/reportes"))

@router.api_route("/api/v1/reportes/{ruta:path}", methods=["GET","POST","PUT","PATCH","DELETE","OPTIONS"], tags=["Reportes"])
async def proxy_reportes(request: Request, ruta: str) -> Response:
    return await reenviar_peticion(request, _ruta(settings.URL_REPORTES, f"/api/v1/reportes/{ruta}"))

# ── Auditoría ─────────────────────────────────────────────────
@router.api_route("/api/v1/auditoria", methods=["GET","POST","OPTIONS"], tags=["Reportes"])
async def proxy_auditoria_raiz(request: Request) -> Response:
    return await reenviar_peticion(request, _ruta(settings.URL_REPORTES, "/api/v1/auditoria/"))

@router.api_route("/api/v1/auditoria/{ruta:path}", methods=["GET","POST","OPTIONS"], tags=["Reportes"])
# BUG-013 FIX: la variable ruta se ignoraba, siempre apuntaba al mismo endpoint
async def proxy_auditoria(request: Request, ruta: str) -> Response:
    return await reenviar_peticion(request, _ruta(settings.URL_REPORTES, f"/api/v1/auditoria/{ruta}"))