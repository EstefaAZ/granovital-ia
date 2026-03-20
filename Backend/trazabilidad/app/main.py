# ==============================================================
# modulo_05_trazabilidad / app/main.py
# ==============================================================

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.api.v1.trazabilidad import router as traza_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Iniciando {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"RN-04: sal de hash = configurada")
    logger.info(f"RF-11: humedad objetivo secado = {settings.SECADO_HUMEDAD_OBJETIVO}%")
    logger.info(f"RF-11: horas minimas secado = {settings.SECADO_HORAS_MINIMAS}h")
    logger.info(f"RN-05: URL base QR = {settings.URL_BASE_SISTEMA}")
    from app.core.database import engine, Base
    from app.models import trazabilidad
    Base.metadata.create_all(bind=engine)
    logger.info("Tablas de Trazabilidad creadas correctamente")
    yield
    logger.info("Modulo Trazabilidad detenido.")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "Modulo 05 — Trazabilidad, Control de Secado y Clasificacion. "
        "RF-10 trazabilidad | RF-11 secado | RF-12 clasificacion grano | "
        "RF-15 QR publico. RN-02 RN-04 RN-05 RNF-05."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.ALLOWED_ORIGINS.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.exception_handler(Exception)
async def error_global(request: Request, exc: Exception) -> JSONResponse:
    logger.error(f"Error no controlado: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Error interno del servidor."},
    )


app.include_router(traza_router, prefix="/api/v1")


@app.get("/", tags=["Sistema"])
def raiz():
    return {"modulo": settings.APP_NAME, "version": settings.APP_VERSION}


@app.get("/health", tags=["Sistema"])
def health():
    return {"estado": "saludable"}
