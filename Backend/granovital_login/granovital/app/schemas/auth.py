# =============================================================
# app/schemas/auth.py
# Esquemas Pydantic — Validación de entrada y salida para auth
# Trazabilidad: RF-01, RF-02 | RNF-04
# =============================================================

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, field_validator, ConfigDict
import re


# =================================================================
# ESQUEMAS DE SOLICITUD (Request)
# =================================================================

class LoginRequest(BaseModel):
    """
    Cuerpo de la solicitud POST /api/v1/auth/login
    Valida que el correo tenga formato válido y que la contraseña
    no esté vacía. No se valida complejidad aquí (ya está en la BD).
    """
    correo: EmailStr
    contrasena: str

    @field_validator("contrasena")
    @classmethod
    def contrasena_no_vacia(cls, v: str) -> str:
        if not v or len(v.strip()) == 0:
            raise ValueError("La contraseña no puede estar vacía")
        if len(v) < 6:
            raise ValueError("La contraseña debe tener al menos 6 caracteres")
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "correo": "caficultor@granovital.co",
                "contrasena": "mi_password_seguro"
            }
        }
    )


class RefreshTokenRequest(BaseModel):
    """
    Cuerpo de la solicitud POST /api/v1/auth/refresh
    El cliente envía su refresh token para obtener un nuevo access token.
    """
    refresh_token: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            }
        }
    )


class CambiarPasswordRequest(BaseModel):
    """
    Cuerpo de la solicitud POST /api/v1/auth/change-password
    Requiere la contraseña actual para confirmar identidad (RNF-04).
    """
    contrasena_actual: str
    contrasena_nueva: str
    contrasena_nueva_confirmar: str

    @field_validator("contrasena_nueva")
    @classmethod
    def validar_fortaleza(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("La contraseña nueva debe tener al menos 8 caracteres")
        if not re.search(r"[A-Z]", v):
            raise ValueError("La contraseña debe contener al menos una letra mayúscula")
        if not re.search(r"[0-9]", v):
            raise ValueError("La contraseña debe contener al menos un número")
        return v

    @field_validator("contrasena_nueva_confirmar")
    @classmethod
    def contrasenas_coinciden(cls, v: str, info) -> str:
        if "contrasena_nueva" in info.data and v != info.data["contrasena_nueva"]:
            raise ValueError("Las contraseñas nuevas no coinciden")
        return v


# =================================================================
# ESQUEMAS DE RESPUESTA (Response)
# =================================================================

class RolResponse(BaseModel):
    """Información del rol del usuario — expuesta en la respuesta de login."""
    id_rol: int
    nombre_rol: str
    descripcion: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class UsuarioLoginResponse(BaseModel):
    """
    Información del usuario retornada tras login exitoso.
    No incluye la contraseña ni campos sensibles internos (RNF-04).
    """
    id_usuario:     int
    nombre:         str
    apellido:       str
    correo:         str
    telefono:       Optional[str] = None
    estado_cuenta:  str
    ultimo_acceso:  Optional[datetime] = None
    rol:            RolResponse

    model_config = ConfigDict(from_attributes=True)


class LoginResponse(BaseModel):
    """
    Respuesta completa del endpoint POST /api/v1/auth/login
    Incluye los tokens JWT y la información del usuario autenticado.
    """
    access_token:  str
    refresh_token: str
    token_type:    str = "bearer"
    expires_in:    int              # Segundos hasta expiración del access token
    usuario:       UsuarioLoginResponse

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "access_token":  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type":    "bearer",
                "expires_in":    3600,
                "usuario": {
                    "id_usuario":    1,
                    "nombre":        "Carlos",
                    "apellido":      "Restrepo",
                    "correo":        "caficultor@granovital.co",
                    "estado_cuenta": "activo",
                    "rol": {
                        "id_rol":     2,
                        "nombre_rol": "Caficultor"
                    }
                }
            }
        }
    )


class RefreshTokenResponse(BaseModel):
    """Respuesta del endpoint de refresco de token."""
    access_token: str
    token_type:   str = "bearer"
    expires_in:   int


class MensajeResponse(BaseModel):
    """Respuesta genérica para operaciones sin datos que retornar."""
    mensaje: str
    exitoso: bool = True


class ErrorResponse(BaseModel):
    """Respuesta de error estandarizada."""
    error:   str
    detalle: Optional[str] = None
    codigo:  Optional[str] = None
