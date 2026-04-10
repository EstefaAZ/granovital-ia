# =============================================================
# app/models/usuario.py
# Modelos ORM SQLAlchemy — tbl_usuario, tbl_rol, tbl_permiso
# Trazabilidad: RF-01, RF-16, RF-17 | RN-01 | RNF-04
# =============================================================

from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column, Integer, String, DateTime, Enum,
    ForeignKey, UniqueConstraint
)
from sqlalchemy.orm import relationship, Mapped, mapped_column
from app.core.database import Base


class Rol(Base):
    """
    tbl_rol — Define los roles del sistema.
    Roles: Administrador, Caficultor, Productor, Comercializador, Consumidor
    Soporta RN-01 (acceso por rol) y RF-17 (asignación de roles).
    """
    __tablename__ = "tbl_rol"

    id_rol: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre_rol: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    descripcion: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    fecha_creacion: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    # Relaciones
    usuarios: Mapped[list["Usuario"]] = relationship("Usuario", back_populates="rol")
    permisos: Mapped[list["RolPermiso"]] = relationship("RolPermiso", back_populates="rol")

    def __repr__(self) -> str:
        return f"<Rol id={self.id_rol} nombre='{self.nombre_rol}'>"


class Permiso(Base):
    """
    tbl_permiso — Catálogo de permisos atómicos del sistema.
    Permite control granular de acceso por módulo (RF-17).
    """
    __tablename__ = "tbl_permiso"

    id_permiso: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre_permiso: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    descripcion: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    modulo: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)

    # Relaciones
    roles: Mapped[list["RolPermiso"]] = relationship("RolPermiso", back_populates="permiso")

    def __repr__(self) -> str:
        return f"<Permiso '{self.nombre_permiso}'>"


class RolPermiso(Base):
    """
    tbl_rol_permiso — Tabla puente rol-permiso.
    Implementa RN-01: el sistema solo permite acceso según el rol asignado.
    """
    __tablename__ = "tbl_rol_permiso"

    id_rol_permiso: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_rol: Mapped[int] = mapped_column(Integer, ForeignKey("tbl_rol.id_rol", ondelete="CASCADE"), nullable=False)
    id_permiso: Mapped[int] = mapped_column(Integer, ForeignKey("tbl_permiso.id_permiso", ondelete="CASCADE"), nullable=False)

    __table_args__ = (
        UniqueConstraint("id_rol", "id_permiso", name="uq_rol_permiso"),
    )

    # Relaciones
    rol: Mapped["Rol"] = relationship("Rol", back_populates="permisos")
    permiso: Mapped["Permiso"] = relationship("Permiso", back_populates="roles")


class Usuario(Base):
    """
    tbl_usuario — Usuarios del sistema GranoVital IA.
    La contraseña se almacena como hash bcrypt (RNF-04).
    El estado_cuenta controla si el usuario puede autenticarse (RF-01).
    """
    __tablename__ = "tbl_usuario"

    id_usuario: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    apellido: Mapped[str] = mapped_column(String(100), nullable=False)
    correo: Mapped[str] = mapped_column(String(150), nullable=False, unique=True)
    contrasena: Mapped[str] = mapped_column(String(255), nullable=False, comment="Hash bcrypt — nunca texto plano")
    telefono: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    tipo_documento: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="Tipo de documento: Cédula, Pasaporte")
    documento: Mapped[str] = mapped_column(String(20), nullable=False, unique=True, comment="Número de documento de identidad")
    municipio: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, comment="Municipio de residencia")
    fecha_registro: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    estado_cuenta: Mapped[str] = mapped_column(
        Enum("activo", "inactivo", "suspendido"),
        nullable=False,
        default="activo"
    )
    intentos_fallidos: Mapped[int] = mapped_column(Integer, nullable=False, default=0,
                               comment="Contador de intentos de login fallidos")
    ultimo_acceso: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True,
                            comment="Fecha del último login exitoso")
    id_rol: Mapped[int] = mapped_column(Integer, ForeignKey("tbl_rol.id_rol"), nullable=False)

    # OAuth Google
    google_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, unique=True,
                           comment="ID único de Google para usuarios OAuth")
    provider: Mapped[str] = mapped_column(String(20), nullable=False, default="local",
                        comment="Proveedor de autenticación: local, google")
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True,
                             comment="URL del avatar del usuario (Google profile picture)")

    # Relaciones
    rol: Mapped["Rol"] = relationship("Rol", back_populates="usuarios")

    @property
    def nombre_completo(self) -> str:
        return f"{self.nombre} {self.apellido}"

    @property
    def esta_activo(self) -> bool:
        return bool(self.estado_cuenta == "activo")

    def __repr__(self) -> str:
        return f"<Usuario id={self.id_usuario} correo='{self.correo}' rol='{self.rol.nombre_rol if self.rol else None}'>"
