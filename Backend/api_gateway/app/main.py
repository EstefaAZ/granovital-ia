# =============================================================
# api_gateway / app/main.py
# Punto de entrada del API Gateway — GranoVital IA
# =============================================================

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.middleware.auth import middleware_auth
from app.routers.gateway import router as gateway_router

logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# =============================================================
# CICLO DE VIDA
# =============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Iniciando {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Microservicios registrados:")
    logger.info(f"  Auth         → {settings.URL_AUTH}")
    logger.info(f"  Cultivos     → {settings.URL_CULTIVOS}")
    logger.info(f"  Monitoreo    → {settings.URL_MONITOREO}")
    logger.info(f"  IA           → {settings.URL_IA}")
    logger.info(f"  Trazabilidad → {settings.URL_TRAZABILIDAD}")
    logger.info(f"  Mercado      → {settings.URL_MERCADO}")
    logger.info(f"  Reportes     → {settings.URL_REPORTES}")
    yield
    logger.info("API Gateway detenido correctamente.")


# =============================================================
# INSTANCIA FastAPI
# =============================================================

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "API Gateway del sistema GranoVital IA. "
        "Punto de entrada único que enruta las peticiones a cada microservicio, "
        "valida el JWT y centraliza el CORS. "
        "Universidad Católica Luis Amigó, 2026."
    ),
    contact={
        "name": "Santy Usuga Graciano & Estefanía Ardila Zuleta",
        "email": "granovital@ucatolicaluisamigo.edu.co",
    },
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)


# =============================================================
# MIDDLEWARES  (orden: CORS → Auth → routers)
# =============================================================

# 1. CORS — debe ir primero para que las preflight requests pasen
allowed_origins = [
    o.strip() for o in settings.ALLOWED_ORIGINS.split(",") if o.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "X-Usuario-Nombre"],
    expose_headers=["X-Total-Count"],
)

# 2. Autenticación JWT
app.add_middleware(BaseHTTPMiddleware, dispatch=middleware_auth)


# =============================================================
# MANEJADOR GLOBAL DE ERRORES
# =============================================================

@app.exception_handler(Exception)
async def error_global(request: Request, exc: Exception) -> JSONResponse:
    logger.error(f"Error no manejado en {request.url}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "Error interno del gateway."},
    )


# =============================================================
# ROUTERS
# =============================================================

app.include_router(gateway_router)


# =============================================================
# ENDPOINTS PROPIOS DEL GATEWAY
# =============================================================

@app.get("/", tags=["Gateway"], summary="Raíz del gateway")
def raiz():
    return {
        "sistema":  settings.APP_NAME,
        "version":  settings.APP_VERSION,
        "estado":   "operativo",
        "docs":     "/docs",
    }


@app.get("/health", tags=["Gateway"], summary="Health check del gateway")
def health():
    return {"estado": "saludable", "version": settings.APP_VERSION}


@app.get("/servicios", tags=["Gateway"], summary="URLs de microservicios registrados")
def servicios():
    """Lista todos los microservicios que gestiona este gateway."""
    return {
        "auth":         settings.URL_AUTH,
        "cultivos":     settings.URL_CULTIVOS,
        "onitoreo":    settings.URL_MONITOREO,
        "ia":           settings.URL_IA,
        "trazabilidad": settings.URL_TRAZABILIDAD,
        "mercado":      settings.URL_MERCADO,
        "reportes":     settings.URL_REPORTES,
    }