# ==============================================================
# modulo_03_monitoreo / app/core/database.py
# Sesion SQLAlchemy - pool configurado para zona rural (RNF-10)
# Pool reducido porque en campo se trabaja con conexiones lentas
# ==============================================================

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,         # Reducido para entornos con recursos limitados
    max_overflow=10,
    pool_recycle=1800,   # 30 min para reconectar antes que MySQL cierre
    connect_args={"connect_timeout": 10},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """
    Dependencia FastAPI. Provee sesion de base de datos y
    garantiza su cierre correcto al terminar la peticion.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
