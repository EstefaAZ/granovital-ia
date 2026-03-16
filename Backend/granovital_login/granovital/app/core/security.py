# =============================================================
# app/core/security.py
# Seguridad: JWT, bcrypt, RBAC, blacklist de tokens
# Requisitos: RF-01, RF-17 | RNF-04 | RN-01
# =============================================================

from datetime import datetime, timedelta, timezone
from typing import Optional, List
import logging

from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db

logger = logging.getLogger(__name__)

# ── Configuración bcrypt ──────────────────────────────────────────
# schemes=["bcrypt"] con factor de costo 12 (RNF-04)
# deprecated="auto" migra automáticamente hashes más antiguos
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ── Esquema de autenticación Bearer ──────────────────────────────
bearer_scheme = HTTPBearer()


# =================================================================
# FUNCIONES DE CONTRASEÑA
# =================================================================

def hash_password(plain_password: str) -> str:
    """
    Genera un hash bcrypt seguro de la contraseña.
    Factor de costo 12 → ~250ms por hash (resistente a fuerza bruta).
    Nunca almacenar la contraseña en texto plano (RNF-04).
    """
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifica que la contraseña ingresada coincida con el hash almacenado.
    Usa comparación de tiempo constante para evitar ataques de timing.
    """
    return pwd_context.verify(plain_password, hashed_password)


# =================================================================
# FUNCIONES JWT
# =================================================================

def create_access_token(
    subject: str,
    role: str,
    extra_data: Optional[dict] = None,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Crea un token JWT de acceso firmado con HS256.

    Args:
        subject:    ID del usuario (como string)
        role:       Nombre del rol del usuario (para RBAC — RN-01)
        extra_data: Datos adicionales a incluir en el payload
        expires_delta: Tiempo de expiración personalizado

    Returns:
        Token JWT firmado como string
    """
    expire = datetime.now(timezone.utc) + (
        expires_delta
        or timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    payload = {
        "sub": subject,          # Subject: ID del usuario
        "role": role,            # Rol para RBAC (RN-01)
        "exp": expire,           # Expiración
        "iat": datetime.now(timezone.utc),  # Issued at
        "type": "access",        # Tipo de token
    }

    if extra_data:
        payload.update(extra_data)

    return jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def create_refresh_token(subject: str) -> str:
    """
    Crea un token de refresco de larga duración.
    Solo contiene el sub y la expiración — sin datos de rol
    para minimizar la información expuesta.
    """
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS
    )

    payload = {
        "sub": subject,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "refresh",
    }

    return jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def decode_token(token: str) -> dict:
    """
    Decodifica y valida un token JWT.

    Raises:
        HTTPException 401: si el token es inválido, expirado o malformado
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return payload
    except JWTError as e:
        logger.warning(f"Token JWT inválido: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de autenticación inválido o expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )


# =================================================================
# DEPENDENCIAS FastAPI — obtención del usuario actual
# =================================================================

def get_current_user_payload(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> dict:
    """
    Dependency de FastAPI que extrae y valida el token JWT del header
    Authorization: Bearer <token>

    Retorna el payload del token para usar en los endpoints.
    """
    payload = decode_token(credentials.credentials)

    # Verificar que sea un access token (no refresh)
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Se requiere un token de acceso válido",
        )

    return payload


def get_current_user_id(
    payload: dict = Depends(get_current_user_payload),
) -> int:
    """Extrae el ID del usuario del payload JWT."""
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token sin identificador de usuario",
        )
    return int(user_id)


def get_current_user_role(
    payload: dict = Depends(get_current_user_payload),
) -> str:
    """Extrae el nombre del rol del usuario desde el payload JWT."""
    role = payload.get("role")
    if not role:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token sin información de rol",
        )
    return role


# =================================================================
# RBAC — Control de acceso basado en roles (RN-01, RF-17)
# =================================================================

def require_roles(*allowed_roles: str):
    """
    Decorador/dependency factory que restringe el acceso a un endpoint
    a los roles especificados. Implementa RN-01 (acceso por rol).

    Uso en router:
        @router.get("/admin/users")
        def list_users(role: str = Depends(require_roles("Administrador"))):
            ...

    Args:
        *allowed_roles: Nombres de roles permitidos para el endpoint

    Returns:
        Dependency de FastAPI que valida el rol del token JWT
    """
    def dependency(
        payload: dict = Depends(get_current_user_payload),
    ) -> str:
        user_role = payload.get("role", "")
        if user_role not in allowed_roles:
            logger.warning(
                f"Acceso denegado: rol '{user_role}' intentó acceder "
                f"a recurso restringido para {allowed_roles}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Acceso denegado. Se requiere uno de los roles: {', '.join(allowed_roles)}",
            )
        return user_role

    return dependency


def require_any_authenticated():
    """
    Dependency que permite acceso a cualquier usuario autenticado,
    sin importar su rol. Útil para endpoints de perfil (RF-02).
    """
    def dependency(
        payload: dict = Depends(get_current_user_payload),
    ) -> dict:
        return payload

    return dependency
