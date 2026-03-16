# modulo_07_reportes / app/main.py
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.core.config import settings
from app.api.v1.reportes import router as reportes_router, auditoria_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    import os
    os.makedirs(settings.REPORTES_DIR, exist_ok=True)
    logger.info(f"Iniciando {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Directorio reportes: {settings.REPORTES_DIR}")
    yield
    logger.info("Módulo Reportes detenido.")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "Módulo 07 — Reportes y Auditoría. "
        "RF-18: generación de reportes del sistema y del cultivo. "
        "Diagrama de estados: Solicitado → Generando → Disponible → Descargado. "
        "Log de auditoría append-only (RNF-05)."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.ALLOWED_ORIGINS.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["Authorization", "Content-Type", "X-Usuario-Nombre"],
)


@app.exception_handler(Exception)
async def error_global(request: Request, exc: Exception) -> JSONResponse:
    logger.error(f"Error no controlado: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "Error interno del servidor."})


app.include_router(reportes_router,  prefix="/api/v1")
app.include_router(auditoria_router, prefix="/api/v1")


@app.get("/",      tags=["Sistema"])
def raiz():
    return {"modulo": settings.APP_NAME, "version": settings.APP_VERSION}

@app.get("/health", tags=["Sistema"])
def health():
    return {"estado": "saludable"}
