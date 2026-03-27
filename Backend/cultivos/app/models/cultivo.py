# ==============================================================
# modulo_02_cultivos / app/models/cultivo.py
# ORM SQLAlchemy - tbl_cultivo, tbl_lote, tbl_sensor
#
# Diagramas de estado implementados:
#   Cultivo:  Creado -> En Seguimiento -> Con Problema / Finalizado / Eliminado
#   Lote:     Registrado -> Disponible -> En Analisis -> Aprobado -> Vendido
#
# Trazabilidad de requisitos:
#   RF-03  Gestion de cultivos
#   RF-04  Registro de lotes
#   RN-02  Trazabilidad obligatoria antes de comercializar
#   RNF-06 Escalabilidad - soporte para nuevos sensores IoT
#   RNF-09 Interoperabilidad con dispositivos externos
# ==============================================================

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, DateTime,
    Numeric, Enum, ForeignKey, Text,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class Cultivo(Base):
    """
    tbl_cultivo - Unidad productiva del caficultor.

    Ciclo de vida segun diagrama de estados oficial:
      crearCultivo     -> estado 'creado'
      iniciarMonitoreo -> estado 'en_seguimiento'
      resultadoIA      -> estado 'con_problema_detectado'
      aplicarRec       -> estado 'tratamiento_aplicado'
      cosecha          -> estado 'finalizado'
      eliminarCultivo  -> estado 'eliminado'

    Cada cultivo pertenece a un usuario (id_usuario) y puede
    contener multiples lotes y sensores IoT.
    """
    __tablename__ = "tbl_cultivo"

    id_cultivo     = Column(Integer, primary_key=True, autoincrement=True)
    nombre_cultivo = Column(String(120), nullable=False)
    ubicacion      = Column(
        String(250), nullable=True,
        comment="Coordenadas GPS o descripcion geografica del predio"
    )
    area_hectareas = Column(
        Numeric(8, 2), nullable=True,
        comment="Extension del cultivo en hectareas"
    )
    variedad_cafe  = Column(
        String(80), nullable=True,
        comment="Ej: Castillo, Caturra, Colombia, Geisha, Tabi"
    )
    fecha_siembra  = Column(DateTime, nullable=True)
    estado         = Column(
        Enum(
            "creado",
            "en_seguimiento",
            "con_problema_detectado",
            "tratamiento_aplicado",
            "finalizado",
            "eliminado",
        ),
        nullable=False,
        default="creado",
        comment="Ciclo de vida del cultivo segun diagrama de estados",
    )
    observaciones  = Column(Text, nullable=True)
    fecha_registro = Column(DateTime, nullable=False, default=datetime.utcnow)
    id_usuario = Column(
    Integer,
    ForeignKey("tbl_usuario.id_usuario", ondelete="CASCADE"),
    nullable=False,
    comment="Caficultor propietario del cultivo",
    )

    # Relaciones
    lotes    = relationship(
        "Lote", back_populates="cultivo", cascade="all, delete-orphan"
    )
    sensores = relationship(
        "Sensor", back_populates="cultivo", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return (
            f"<Cultivo id={self.id_cultivo} "
            f"nombre='{self.nombre_cultivo}' estado='{self.estado}'>"
        )


class Lote(Base):
    """
    tbl_lote - Subunidad productiva para control de produccion.

    Ciclo de vida segun diagrama de estados oficial:
      registrarLote    -> estado 'registrado'
      confirmarReg.    -> estado 'disponible'
      enviarAAnalisis  -> estado 'en_analisis'
      resultadoIA ok   -> estado 'aprobado'
      resultadoIA def. -> estado 'con_problema'
      ventaRealizada   -> estado 'vendido'
      eliminarLote     -> estado 'eliminado'

    RN-02: un lote no puede pasar a 'vendido' sin tener la
    etapa 'comercializacion' registrada en tbl_trazabilidad.

    El campo codigo_qr habilita la consulta publica del
    consumidor mediante escaneo (RF-15).
    """
    __tablename__ = "tbl_lote"

    id_lote        = Column(Integer, primary_key=True, autoincrement=True)
    codigo_lote    = Column(
        String(50), nullable=False, unique=True,
        comment="Codigo interno del lote. Formato: LOT-AAAA-NNN"
    )
    codigo_qr      = Column(
        String(64), nullable=True, unique=True,
        comment="Token URL-safe para consulta publica QR (RF-15)"
    )
    fecha_cosecha  = Column(DateTime, nullable=True)
    cantidad_kg    = Column(
        Numeric(10, 2), nullable=True,
        comment="Kilogramos de cafe cereza cosechados"
    )
    estado_lote    = Column(
        Enum(
            "registrado",
            "disponible",
            "en_analisis",
            "aprobado",
            "con_problema",
            "vendido",
            "eliminado",
        ),
        nullable=False,
        default="registrado",
        comment="Ciclo de vida del lote segun diagrama de estados",
    )
    observaciones  = Column(Text, nullable=True)
    fecha_registro = Column(DateTime, nullable=False, default=datetime.utcnow)
    id_cultivo     = Column(
        Integer,
        ForeignKey("tbl_cultivo.id_cultivo", ondelete="CASCADE"),
        nullable=False,
    )

    # Relaciones
    cultivo = relationship("Cultivo", back_populates="lotes")

    def __repr__(self) -> str:
        return (
            f"<Lote id={self.id_lote} "
            f"codigo='{self.codigo_lote}' estado='{self.estado_lote}'>"
        )


class Sensor(Base):
    """
    tbl_sensor - Dispositivos IoT registrados en un cultivo.

    RNF-06: el diseno permite agregar nuevos sensores sin
    modificar la arquitectura existente.
    RNF-09: los sensores transmiten datos via protocolo MQTT
    al suscriptor del modulo de monitoreo ambiental.
    """
    __tablename__ = "tbl_sensor"

    id_sensor         = Column(Integer, primary_key=True, autoincrement=True)
    codigo_sensor     = Column(String(50), nullable=False, unique=True)
    tipo_sensor       = Column(
        Enum("temperatura", "humedad", "suelo", "radiacion", "multivariable"),
        nullable=False,
        comment="Tipo de variable que mide el sensor",
    )
    descripcion       = Column(String(200), nullable=True)
    unidad_medida     = Column(
        String(20), nullable=True,
        comment="Ej: C, %, mm, W/m2"
    )
    fecha_instalacion = Column(DateTime, nullable=True)
    estado            = Column(
        Enum("activo", "inactivo", "falla"),
        nullable=False,
        default="activo",
    )
    id_cultivo        = Column(
        Integer,
        ForeignKey("tbl_cultivo.id_cultivo", ondelete="CASCADE"),
        nullable=False,
    )

    cultivo = relationship("Cultivo", back_populates="sensores")

    def __repr__(self) -> str:
        return (
            f"<Sensor id={self.id_sensor} "
            f"codigo='{self.codigo_sensor}' tipo='{self.tipo_sensor}'>"
        )
