# =============================================================
# app/core/database.py
# Gestión de la sesión SQLAlchemy con MySQL (PyMySQL)
# Requisitos: RNF-03 (disponibilidad), RNF-04 (seguridad)
# =============================================================

from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
from app.core.config import settings


# Motor de base de datos con pool de conexiones configurado
# pool_pre_ping: verifica que la conexión esté viva antes de usarla
# pool_recycle: recicla conexiones cada 30 minutos (evita timeouts MySQL)
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=1800,
    pool_size=10,
    max_overflow=20,
    echo=settings.DEBUG,
)

# Fábrica de sesiones — autocommit=False garantiza control manual
# de transacciones (ACID — RNF-05 integridad de datos)
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# Clase base para todos los modelos ORM del proyecto
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    Dependency de FastAPI que provee una sesión de base de datos
    por solicitud HTTP y la cierra correctamente al finalizar,
    incluso si ocurre una excepción.

    Uso en routers:
        db: Session = Depends(get_db)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
