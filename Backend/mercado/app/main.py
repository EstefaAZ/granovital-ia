# modulo_06_mercado / app/main.py
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.core.config import settings
from app.api.v1.mercado import router as mercado_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Iniciando {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"RF-13: histórico precios = {settings.MESES_HISTORICO_PRECIO} meses")
    logger.info(f"RF-14: histórico demanda = {settings.MESES_HISTORICO_DEMANDA} meses")
    logger.info(f"Umbral alerta variación = {settings.UMBRAL_VARIACION_ALERTA_PCT}%")
    yield
    logger.info("Módulo Mercado detenido.")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "Módulo 06 — Mercado y Análisis de Precios y Demanda. "
        "RF-13 análisis de precios | RF-14 análisis de demanda. "
        "RN-01 acceso por rol Comercializador."
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


app.include_router(mercado_router, prefix="/api/v1")


@app.get("/", tags=["Sistema"])
def raiz():
    return {"modulo": settings.APP_NAME, "version": settings.APP_VERSION}


@app.get("/health", tags=["Sistema"])
def health():
    return {"estado": "saludable"}
