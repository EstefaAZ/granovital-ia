# ==============================================================
# modulo_07_reportes / app/core/config.py
#
# RF-18  Generación de reportes del sistema y del cultivo
# RNF-01 Respuesta < 5 segundos (reportes síncronos sobre datos reales)
# RNF-04 Seguridad — solo Administrador accede a auditoría completa
# RNF-05 Integridad — los registros de auditoría son inmutables
#
# DIAGRAMA DE ESTADOS REPORTE (del documento oficial):
#   Solicitado → Generando → Disponible → Descargado
#                          ↘ Error → (reintentar) → Solicitado
#
# DECISIÓN ARQUITECTÓNICA:
#   Los reportes se generan de forma SÍNCRONA en esta implementación.
#   El diagrama de estados es honrado en el ORM (campo 'estado'),
#   pero la transición Solicitado→Generando→Disponible ocurre dentro
#   de la misma petición HTTP, lo cual cumple RNF-01 para los volúmenes
#   de datos esperados en una finca cafetera (cientos de registros, no
#   millones). Si el proyecto escala, la transición a Celery (async)
#   no requiere cambios en el modelo de datos, solo en el servicio.
# ==============================================================

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME:    str = "GranoVital IA - Modulo Reportes"
    APP_VERSION: str = "1.0.0"
    DEBUG:       bool = False

    DATABASE_URL: str = (
        "mysql+pymysql://granovital:granovital123@localhost:3306/granovital_db"
    )
    SECRET_KEY: str = "cambia-esta-clave-en-produccion"
    ALGORITHM:  str = "HS256"
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    # Directorio donde se almacenan los PDFs generados
    REPORTES_DIR: str = "/tmp/granovital_reportes"

    # Nombre de la organización en el encabezado del PDF
    NOMBRE_ORGANIZACION: str = "GranoVital IA"
    LOGO_PATH:           str = ""  # ruta opcional al logo

    # Máximo de registros de auditoría por página (paginación)
    AUDITORIA_PAGE_SIZE: int = 50

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
