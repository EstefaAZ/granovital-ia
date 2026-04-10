# =============================================================
# app/main.py
# Punto de entrada principal de GranoVital IA — FastAPI
# Trazabilidad: RNF-01 (rendimiento), RNF-03 (disponibilidad)
#               RNF-04 (seguridad — CORS controlado)
# =============================================================

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.api.v1 import auth as auth_router

# Configuración de logging estructurado
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# =============================================================
# CICLO DE VIDA DE LA APLICACIÓN
# =============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Iniciando {settings.APP_NAME} v{settings.APP_VERSION}")
    from app.core.database import engine, Base
    from app.models import usuario
    Base.metadata.create_all(bind=engine)
    logger.info("Tablas creadas correctamente")
    yield
    logger.info("Apagando la aplicación correctamente")


# =============================================================
# INSTANCIA PRINCIPAL FastAPI
# =============================================================

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "API REST del sistema GranoVital IA — Implementación de Inteligencia Artificial "
        "en la Gestión del Café. Universidad Católica Luis Amigó, 2026."
    ),
    contact={
        "name": "Santy Usuga Graciano & Estefanía Ardila Zuleta",
        "email": "granovital@ucatolicaluisamigo.edu.co",
    },
    docs_url="/docs",        # Swagger UI (solo en desarrollo)
    redoc_url="/redoc",      # ReDoc UI
    openapi_url="/openapi.json",
    lifespan=lifespan,
)


# =============================================================
# MIDDLEWARE CORS — RNF-04 (solo orígenes autorizados)
# =============================================================

allowed_origins = [
    origin.strip()
    for origin in settings.ALLOWED_ORIGINS.split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,          # Necesario para cookies con tokens
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
    expose_headers=["X-Total-Count"],
)


# =============================================================
# MANEJADORES GLOBALES DE ERRORES
# =============================================================

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Captura errores no manejados para evitar exponer stack traces
    en producción (RNF-04 — seguridad de la información).
    """
    # No manejar HTTPException, dejar que FastAPI lo maneje
    if isinstance(exc, HTTPException):
        raise exc
    
    logger.error(f"Error no manejado en {request.url}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Error interno del servidor",
            "detalle": "Se ha producido un error inesperado. Por favor contacte al administrador.",
        },
    )


# =============================================================
# REGISTRO DE ROUTERS
# =============================================================

# Prefijo global de la API versión 1
API_V1_PREFIX = "/api/v1"

app.include_router(auth_router.router, prefix=API_V1_PREFIX)


# =============================================================
# ENDPOINTS DE SALUD Y RAÍZ
# =============================================================

@app.get("/", tags=["Sistema"], summary="Raíz de la API")
def root():
    return {
        "sistema":  settings.APP_NAME,
        "version":  settings.APP_VERSION,
        "estado":   "operativo",
        "docs":     "/docs",
    }


@app.get("/health", tags=["Sistema"], summary="Health check")
def health_check():
    """
    Endpoint de verificación de salud.
    Usado por Docker y load balancers para monitorear disponibilidad (RNF-03).
    """
    return {
        "estado":  "saludable",
        "version": settings.APP_VERSION,
    }
