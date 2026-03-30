# ==============================================================
# modulo_02_cultivos / app/core/security.py
# Validacion de JWT y control de acceso por rol (RBAC)
# RN-01 Acceso por rol | RNF-04 Seguridad
# El token fue emitido por el Modulo 01 - Autenticacion
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
    Decodifica y valida el JWT emitido por el Modulo 01.
    Lanza HTTP 401 si el token es invalido o expiro.
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY.get_secret_value(),
            algorithms=[settings.ALGORITHM],
        )
        return payload
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
    Ejemplo de uso: Depends(require_roles("Caficultor", "Administrador"))
    Rechaza con HTTP 403 si el rol del token no esta en la lista permitida.
    """
    def _verificar(payload: dict = Depends(get_current_user_payload)) -> str:
        rol_usuario = payload.get("role", "")
        if rol_usuario not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Acceso denegado. Su rol '{rol_usuario}' no tiene permiso. "
                    f"Roles permitidos: {list(roles)}"
                ),
            )
        return rol_usuario
    return _verificar
