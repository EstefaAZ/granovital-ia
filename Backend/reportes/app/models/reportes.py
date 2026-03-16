# ==============================================================
# modulo_07_reportes / app/models/reportes.py
# ORM SQLAlchemy
#
# tbl_reporte          RF-18  histórico de reportes generados
# tbl_auditoria        RF-18  log de auditoría inmutable del sistema
#
# DIAGRAMA DE ESTADOS (del documento oficial):
#   solicitado → generando → disponible → descargado
#                          ↘ error
#
# tbl_reporte implementa este ciclo completo con el campo 'estado'.
#
# tbl_auditoria:
#   Registra TODA acción relevante en el sistema con actor, módulo,
#   acción, entidad afectada, IP y resultado. Es append-only (RNF-05).
#   El Administrador puede consultarla pero nunca modificarla.
#   No tiene FK a otras tablas a propósito: los registros de auditoría
#   deben subsistir aunque se eliminen los registros originales.
# ==============================================================

from datetime import datetime
from sqlalchemy import (
    Boolean, Column, DateTime, Enum, Integer,
    String, Text,
)
from app.core.database import Base


TIPOS_REPORTE = (
    "cultivos",          # RF-18: resumen de cultivos y lotes
    "trazabilidad",      # RF-18: lotes y cadena de trazabilidad
    "fitosanitario",     # RF-18: análisis IA enfermedades/plagas
    "ambiental",         # RF-18: lecturas de sensores ambientales
    "mercado",           # RF-18: precios y demanda
    "usuarios",          # RF-18: usuarios del sistema (solo Admin)
    "general",           # RF-18: resumen ejecutivo del sistema
)

ESTADOS_REPORTE = ("solicitado", "generando", "disponible", "error", "descargado")

MODULOS_SISTEMA = (
    "autenticacion", "cultivos", "monitoreo", "ia",
    "trazabilidad", "mercado", "reportes", "sistema",
)

ACCIONES_AUDITORIA = (
    "crear", "leer", "actualizar", "eliminar",
    "login", "logout", "exportar", "generar_reporte",
    "cambio_estado", "error_sistema",
)


class Reporte(Base):
    """
    tbl_reporte — RF-18
    Historiza cada reporte generado por el Administrador.
    Implementa el diagrama de estados oficial del proyecto.

    El campo ruta_archivo almacena la ruta relativa del PDF generado
    en el servidor. En producción se sustituiría por una URL de S3
    o almacenamiento equivalente.
    """
    __tablename__ = "tbl_reporte"

    id_reporte      = Column(Integer, primary_key=True, autoincrement=True)
    tipo_reporte    = Column(Enum(*TIPOS_REPORTE), nullable=False)
    nombre          = Column(
        String(200), nullable=False,
        comment="Nombre descriptivo legible para el Administrador",
    )
    parametros      = Column(
        Text, nullable=True,
        comment="JSON con los parámetros usados para generar el reporte",
    )
    # Diagrama de estados del documento oficial
    estado          = Column(
        Enum(*ESTADOS_REPORTE), nullable=False, default="solicitado"
    )
    ruta_archivo    = Column(String(500), nullable=True)
    nombre_archivo  = Column(String(200), nullable=True)
    tamano_bytes    = Column(Integer, nullable=True)
    num_registros   = Column(
        Integer, nullable=True,
        comment="Cantidad de registros incluidos en el reporte",
    )
    mensaje_error   = Column(String(500), nullable=True)
    # Trazabilidad del reporte mismo
    id_usuario      = Column(Integer, nullable=False)
    nombre_usuario  = Column(
        String(150), nullable=True,
        comment="Desnormalizado para que el log sea autocontenido",
    )
    fecha_solicitud = Column(DateTime, nullable=False, default=datetime.utcnow)
    fecha_generado  = Column(DateTime, nullable=True)
    fecha_descarga  = Column(DateTime, nullable=True)

    def __repr__(self):
        return (
            f"<Reporte tipo={self.tipo_reporte} "
            f"estado={self.estado} id={self.id_reporte}>"
        )


class RegistroAuditoria(Base):
    """
    tbl_auditoria — RF-18 (log de auditoría)
    Registro append-only de todas las acciones relevantes del sistema.

    DISEÑO DELIBERADO:
      - Sin FK a otras tablas: un registro de auditoría debe
        persistir aunque el usuario o entidad auditada sea eliminado.
      - Sin endpoint de DELETE o UPDATE: el servicio solo expone
        INSERT y SELECT (RNF-05 integridad de datos).
      - El id_entidad y tipo_entidad identifican qué objeto fue afectado
        (ej: id_lote=42, tipo_entidad="lote").
    """
    __tablename__ = "tbl_auditoria"

    id_auditoria   = Column(Integer, primary_key=True, autoincrement=True)
    modulo         = Column(Enum(*MODULOS_SISTEMA), nullable=False)
    accion         = Column(Enum(*ACCIONES_AUDITORIA), nullable=False)
    tipo_entidad   = Column(
        String(80), nullable=True,
        comment="Nombre de la entidad afectada: lote, cultivo, usuario...",
    )
    id_entidad     = Column(
        Integer, nullable=True,
        comment="ID del registro afectado en su tabla de origen",
    )
    descripcion    = Column(
        Text, nullable=False,
        comment="Descripción humana de lo que ocurrió",
    )
    resultado      = Column(
        Enum("exitoso", "fallido", "parcial"), nullable=False, default="exitoso"
    )
    id_usuario     = Column(Integer, nullable=True)
    nombre_usuario = Column(String(150), nullable=True)
    rol_usuario    = Column(String(60), nullable=True)
    ip_origen      = Column(String(50), nullable=True)
    user_agent     = Column(String(300), nullable=True)
    dato_anterior  = Column(
        Text, nullable=True,
        comment="JSON del valor antes del cambio (para auditoría de modificaciones)",
    )
    dato_nuevo     = Column(
        Text, nullable=True,
        comment="JSON del valor después del cambio",
    )
    fecha_evento   = Column(DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return (
            f"<Auditoria {self.modulo}.{self.accion} "
            f"usuario={self.id_usuario} {self.fecha_evento}>"
        )
