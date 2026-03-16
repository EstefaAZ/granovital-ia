# modulo_06_mercado / app/core/security.py  — RN-01 RBAC
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from app.core.config import settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

def get_current_user_payload(token: str = Depends(oauth2_scheme)) -> dict:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalido o expirado.",
            headers={"WWW-Authenticate": "Bearer"},
        )

def get_current_user_id(payload: dict = Depends(get_current_user_payload)) -> int:
    return int(payload["sub"])

def require_roles(*roles: str):
    def _check(payload: dict = Depends(get_current_user_payload)) -> str:
        rol = payload.get("role", "")
        if rol not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Acceso denegado. Rol '{rol}' no autorizado.",
            )
        return rol
    return _check
