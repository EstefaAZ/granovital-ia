# ==============================================================
# modulo_03_monitoreo / app/core/security.py
# Validacion de JWT y RBAC - heredado del Modulo 01
# RN-01 Acceso por rol | RNF-04 Seguridad
# ==============================================================

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from app.core.config import settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user_payload(
    token: str = Depends(oauth2_scheme),
) -> dict:
    """
    Decodifica el JWT emitido por el Modulo 01.
    Lanza HTTP 401 si el token es invalido o expiro.
    """
    try:
        return jwt.decode(
            token,
            settings.SECRET_KEY.get_secret_value(),
            algorithms=[settings.ALGORITHM],
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalido o expirado. Inicie sesion nuevamente.",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_user_id(
    payload: dict = Depends(get_current_user_payload),
) -> int:
    """Extrae el ID del usuario autenticado desde el payload JWT."""
    return int(payload["sub"])


def require_roles(*roles: str):
    """
    RN-01: fabrica de dependencias para RBAC.
    Rechaza con HTTP 403 si el rol no esta entre los permitidos.
    """
    def _verificar(payload: dict = Depends(get_current_user_payload)) -> str:
        rol = payload.get("role", "")
        if rol not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Acceso denegado. Rol '{rol}' no tiene permiso. "
                    f"Roles permitidos: {list(roles)}"
                ),
            )
        return rol
    return _verificar
