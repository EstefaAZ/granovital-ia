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


class RegisterRequest(BaseModel):
    """
    Cuerpo de la solicitud POST /api/v1/auth/register
    """
    # Paso 1: Datos personales
    nombre: str
    correo: EmailStr
    contrasena: str
    telefono: str
    tipo_documento: str  # "Cédula de ciudadanía" o "Pasaporte"
    documento: str
    municipio: str

    # Paso 2: Rol
    rol: str

    # Paso 3: Datos específicos por rol
    # Admin
    codigo_autorizacion: Optional[str] = None
    institucion: Optional[str] = None

    # Caficultor
    nombre_finca: Optional[str] = None
    vereda: Optional[str] = None
    area_cultivada: Optional[float] = None
    altitud: Optional[int] = None
    variedad_principal: Optional[str] = None
    sistema_cultivo: Optional[str] = None
    tipo_proceso: Optional[str] = None
    unidades_preferidas: Optional[str] = None
    canal_alertas: Optional[str] = None

    # Productor
    nombre_finca_planta: Optional[str] = None
    vereda_productor: Optional[str] = None
    area_cultivada_productor: Optional[float] = None
    altitud_productor: Optional[int] = None
    variedad_principal_productor: Optional[str] = None
    tipos_proceso: Optional[list[str]] = None
    presta_maquila: Optional[str] = None
    unidades_preferidas_productor: Optional[str] = None
    canal_alertas_productor: Optional[str] = None

    # Comercializador
    nombre_empresa: Optional[str] = None
    nit: Optional[str] = None
    dv: Optional[str] = None
    tipo_comercializador: Optional[str] = None
    region_interes: Optional[str] = None
    preferencia_calidad: Optional[str] = None

    # Consumidor
    apodo: Optional[str] = None
    pais_residencia: Optional[str] = None
    preferencia_cafe: Optional[str] = None

    # Paso 4: Confirmación
    codigo_verificacion: str

    @field_validator("contrasena")
    @classmethod
    def validar_contrasena(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("La contraseña debe tener al menos 8 caracteres")
        if not re.search(r"[A-Z]", v):
            raise ValueError("La contraseña debe contener al menos una letra mayúscula")
        if not re.search(r"[0-9]", v):
            raise ValueError("La contraseña debe contener al menos un número")
        return v

    @field_validator("nombre")
    @classmethod
    def validar_nombre(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("El nombre completo es obligatorio")
        if not re.match(r"^[a-záéíóúñüA-ZÁÉÍÓÚÑÜ\s]+$", v):
            raise ValueError("El nombre solo debe contener letras y espacios")
        if len(v.strip()) < 2:
            raise ValueError("El nombre debe tener al menos 2 caracteres")
        return v.strip()

    @field_validator("telefono")
    @classmethod
    def validar_telefono(cls, v: str) -> str:
        if not re.match(r"^\d{10}$", v):
            raise ValueError("El teléfono debe tener exactamente 10 dígitos")
        return v

    @field_validator("documento")
    @classmethod
    def validar_documento(cls, v: str, info) -> str:
        tipo = info.data.get("tipo_documento")
        if tipo == "Cédula de ciudadanía":
            if not re.match(r"^\d{10}$", v):
                raise ValueError("La cédula debe tener exactamente 10 dígitos")
        elif tipo == "Pasaporte":
            if not re.match(r"^[A-Za-z0-9]{6,9}$", v):
                raise ValueError("El pasaporte debe tener 6-9 caracteres alfanuméricos")
        return v

    @field_validator("nit")
    @classmethod
    def validar_nit(cls, v: str) -> str:
        if v and not re.match(r"^\d{9}$", v):
            raise ValueError("El NIT debe tener exactamente 9 dígitos")
        return v

    @field_validator("dv")
    @classmethod
    def validar_dv(cls, v: str) -> str:
        if v and not re.match(r"^\d$", v):
            raise ValueError("El dígito de verificación debe ser un número")
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "nombre": "Juan Pérez",
                "correo": "juan@correo.com",
                "contrasena": "Password123",
                "telefono": "3001234567",
                "tipo_documento": "Cédula de ciudadanía",
                "documento": "1234567890",
                "municipio": "Armenia",
                "rol": "Caficultor",
                "nombre_finca": "Finca El Café",
                "vereda": "La Esperanza",
                "area_cultivada": 5.5,
                "variedad_principal": "Caturra",
                "sistema_cultivo": "tecnificado",
                "tipo_proceso": "lavado",
                "unidades_preferidas": "kg",
                "canal_alertas": "WhatsApp",
                "codigo_verificacion": "A1B2C"
            }
        }
    )


class SendVerificationCodeRequest(BaseModel):
    """
    Cuerpo de la solicitud POST /api/v1/auth/send-verification-code
    """
    correo: EmailStr

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "correo": "usuario@correo.com"
            }
        }
    )


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
    provider:       str = "local"  # Proveedor de autenticación: local, google
    avatar_url:     Optional[str] = None  # URL del avatar del usuario

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


# =================================================================
# ESQUEMAS DE GOOGLE OAUTH
# =================================================================

class GoogleAuthURLResponse(BaseModel):
    """
    Respuesta con la URL de autorización de Google OAuth.
    """
    auth_url: str
    state: Optional[str] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "auth_url": "https://accounts.google.com/o/oauth2/auth?...",
                "state": "random_state_string"
            }
        }
    )


class GoogleOAuthCallbackRequest(BaseModel):
    """
    Solicitud del callback de Google OAuth.
    """
    code: str
    state: Optional[str] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "code": "4/0AZEOvhV...",
                "state": "random_state_string"
            }
        }
    )


class GoogleOAuthResponse(BaseModel):
    """
    Respuesta completa de autenticación OAuth de Google.
    Similar a LoginResponse pero incluye campos específicos de OAuth.
    """
    access_token:  str
    refresh_token: str
    token_type:    str = "bearer"
    expires_in:    int
    usuario:       UsuarioLoginResponse

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 3600,
                "usuario": {
                    "id_usuario": 1,
                    "nombre": "Juan",
                    "apellido": "Pérez",
                    "correo": "juan.perez@gmail.com",
                    "telefono": None,
                    "estado_cuenta": "activo",
                    "ultimo_acceso": "2024-01-15T10:30:00Z",
                    "rol": {
                        "id_rol": 4,
                        "nombre_rol": "Consumidor",
                        "descripcion": "Usuario final consumidor"
                    }
                }
            }
        }
    )
