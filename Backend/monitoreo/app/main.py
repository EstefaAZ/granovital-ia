# ==============================================================
# modulo_03_monitoreo / app/main.py
# Punto de entrada - Modulo de Monitoreo Ambiental y Suelo
# RNF-03 Disponibilidad | RNF-04 CORS seguro
# ==============================================================

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.api.v1.monitoreo import router as monitoreo_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Iniciando {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(
        f"RN-03: umbral de datos validos = {settings.HORAS_DATOS_VALIDOS} horas"
    )
    yield
    logger.info("Modulo de Monitoreo detenido correctamente")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "Modulo de Monitoreo Ambiental y Suelo - GranoVital IA. "
        "RF-03: registro y consulta de variables ambientales. "
        "RF-04: registro y consulta del estado del suelo. "
        "RN-03: validacion de frescura de datos para modulo de IA."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS - RNF-04
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.ALLOWED_ORIGINS.split(",")],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# Manejador global de errores no controlados
@app.exception_handler(Exception)
async def error_global(request: Request, exc: Exception) -> JSONResponse:
    logger.error(f"Error no controlado en {request.url}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Error interno del servidor. Contacte al administrador."},
    )

app.include_router(monitoreo_router, prefix="/api/v1")


@app.get("/", tags=["Sistema"])
def raiz() -> dict:
    return {
        "modulo":  settings.APP_NAME,
        "version": settings.APP_VERSION,
        "estado":  "operativo",
        "docs":    "/docs",
    }


@app.get("/health", tags=["Sistema"])
def health() -> dict:
    """RNF-03: health check para load balancer y Docker."""
    return {"estado": "saludable"}
