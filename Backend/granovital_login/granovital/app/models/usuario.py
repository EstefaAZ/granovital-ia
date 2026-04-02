# =============================================================
# app/models/usuario.py
# Modelos ORM SQLAlchemy — tbl_usuario, tbl_rol, tbl_permiso
# Trazabilidad: RF-01, RF-16, RF-17 | RN-01 | RNF-04
# =============================================================

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, DateTime, Enum,
    ForeignKey, UniqueConstraint
)
from sqlalchemy.orm import relationship
from app.core.database import Base


class Rol(Base):
    """
    tbl_rol — Define los roles del sistema.
    Roles: Administrador, Caficultor, Productor, Comercializador, Consumidor
    Soporta RN-01 (acceso por rol) y RF-17 (asignación de roles).
    """
    __tablename__ = "tbl_rol"

    id_rol        = Column(Integer, primary_key=True, autoincrement=True)
    nombre_rol    = Column(String(50), nullable=False, unique=True)
    descripcion   = Column(String(150), nullable=True)
    fecha_creacion = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relaciones
    usuarios   = relationship("Usuario", back_populates="rol")
    permisos   = relationship("RolPermiso", back_populates="rol")

    def __repr__(self) -> str:
        return f"<Rol id={self.id_rol} nombre='{self.nombre_rol}'>"


class Permiso(Base):
    """
    tbl_permiso — Catálogo de permisos atómicos del sistema.
    Permite control granular de acceso por módulo (RF-17).
    """
    __tablename__ = "tbl_permiso"

    id_permiso     = Column(Integer, primary_key=True, autoincrement=True)
    nombre_permiso = Column(String(100), nullable=False, unique=True)
    descripcion    = Column(String(200), nullable=True)
    modulo         = Column(String(80), nullable=True)

    # Relaciones
    roles = relationship("RolPermiso", back_populates="permiso")

    def __repr__(self) -> str:
        return f"<Permiso '{self.nombre_permiso}'>"


class RolPermiso(Base):
    """
    tbl_rol_permiso — Tabla puente rol-permiso.
    Implementa RN-01: el sistema solo permite acceso según el rol asignado.
    """
    __tablename__ = "tbl_rol_permiso"

    id_rol_permiso = Column(Integer, primary_key=True, autoincrement=True)
    id_rol         = Column(Integer, ForeignKey("tbl_rol.id_rol", ondelete="CASCADE"), nullable=False)
    id_permiso     = Column(Integer, ForeignKey("tbl_permiso.id_permiso", ondelete="CASCADE"), nullable=False)

    __table_args__ = (
        UniqueConstraint("id_rol", "id_permiso", name="uq_rol_permiso"),
    )

    # Relaciones
    rol     = relationship("Rol", back_populates="permisos")
    permiso = relationship("Permiso", back_populates="roles")


class Usuario(Base):
    """
    tbl_usuario — Usuarios del sistema GranoVital IA.
    La contraseña se almacena como hash bcrypt (RNF-04).
    El estado_cuenta controla si el usuario puede autenticarse (RF-01).
    """
    __tablename__ = "tbl_usuario"

    id_usuario     = Column(Integer, primary_key=True, autoincrement=True)
    nombre         = Column(String(100), nullable=False)
    apellido       = Column(String(100), nullable=False)
    correo         = Column(String(150), nullable=False, unique=True)
    contrasena     = Column(String(255), nullable=False, comment="Hash bcrypt — nunca texto plano")
    telefono       = Column(String(20), nullable=True)
    fecha_registro = Column(DateTime, nullable=False, default=datetime.utcnow)
    estado_cuenta  = Column(
        Enum("activo", "inactivo", "suspendido"),
        nullable=False,
        default="activo"
    )
    intentos_fallidos = Column(Integer, nullable=False, default=0,
                               comment="Contador de intentos de login fallidos")
    ultimo_acceso  = Column(DateTime, nullable=True,
                            comment="Fecha del último login exitoso")
    id_rol         = Column(Integer, ForeignKey("tbl_rol.id_rol"), nullable=False)

    # Relaciones
    rol = relationship("Rol", back_populates="usuarios")

    @property
    def nombre_completo(self) -> str:
        return f"{self.nombre} {self.apellido}"

    @property
    def esta_activo(self) -> bool:
        return bool(self.estado_cuenta == "activo")

    def __repr__(self) -> str:
        return f"<Usuario id={self.id_usuario} correo='{self.correo}' rol='{self.rol.nombre_rol if self.rol else None}'>"
