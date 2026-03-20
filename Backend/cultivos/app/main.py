# ==============================================================
# modulo_02_cultivos / app/main.py
# Punto de entrada - Modulo de Gestion de Cultivos y Lotes
# RNF-03 Disponibilidad | RNF-04 CORS seguro
# ==============================================================

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.v1.cultivos import router as cultivos_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Iniciando {settings.APP_NAME} v{settings.APP_VERSION}")
    from app.core.database import engine, Base
    from app.models import cultivo
    Base.metadata.create_all(bind=engine)
    logger.info("Tablas de Cultivos creadas correctamente")
    yield
    logger.info("Modulo de Cultivos detenido correctamente")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "Modulo de Gestion de Cultivos y Lotes - GranoVital IA. "
        "RF-03: Gestion de cultivos. RF-04: Registro de lotes. "
        "RN-02: Trazabilidad obligatoria antes de comercializar."
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

app.include_router(cultivos_router, prefix="/api/v1")


@app.get("/", tags=["Sistema"])
def raiz():
    return {
        "modulo":  settings.APP_NAME,
        "version": settings.APP_VERSION,
        "estado":  "operativo",
        "docs":    "/docs",
    }


@app.get("/health", tags=["Sistema"])
def health():
    """RNF-03: health check para load balancer y Docker."""
    return {"estado": "saludable"}
