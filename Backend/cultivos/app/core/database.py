# ==============================================================
# modulo_02_cultivos / app/core/database.py
# Sesion de base de datos SQLAlchemy
# RNF-05 Integridad de datos | RNF-06 Escalabilidad (pool)
# ==============================================================

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    pool_recycle=3600,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """
    Dependencia FastAPI. Provee una sesion de base de datos
    y garantiza su cierre correcto al terminar la peticion.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
