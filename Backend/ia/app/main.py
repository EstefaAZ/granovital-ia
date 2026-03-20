# ==============================================================
# modulo_04_ia / app/main.py
# Punto de entrada - Modulo de Inteligencia Artificial
# ==============================================================

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.api.v1.ia import router as ia_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Iniciando {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"RNF-01: timeout inferencia = {settings.TIMEOUT_INFERENCIA_SEG}s")
    logger.info(f"RN-03:  umbral datos validos = {settings.HORAS_DATOS_VALIDOS}h")
    logger.info(f"RNF-08: directorio modelos = {settings.DIR_MODELOS}")
    from app.core.database import engine, Base
    from app.models import analisis
    Base.metadata.create_all(bind=engine)
    logger.info("Tablas de IA creadas correctamente")
    yield
    logger.info("Modulo IA detenido.")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "Modulo 04 - Inteligencia Artificial GranoVital IA. "
        "RF-05 deteccion enfermedades | RF-06 plagas | "
        "RF-07 prediccion fitosanitaria | "
        "RF-08 riego | RF-09 fertilizacion."
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


app.include_router(ia_router, prefix="/api/v1")


@app.get("/", tags=["Sistema"])
def raiz():
    return {"modulo": settings.APP_NAME, "version": settings.APP_VERSION}


@app.get("/health", tags=["Sistema"])
def health():
    return {"estado": "saludable"}
