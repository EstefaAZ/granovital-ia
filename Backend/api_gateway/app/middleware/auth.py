import logging
from fastapi import Request, HTTPException, status
from jose import JWTError, jwt

from app.core.config import settings

logger = logging.getLogger(__name__)

RUTAS_PUBLICAS = {
    "/",
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/api/v1/auth/login",
    "/api/v1/auth/refresh",
}


def es_ruta_publica(path: str) -> bool:
    if path in RUTAS_PUBLICAS:
        return True
    if path.startswith("/api/v1/trazabilidad/qr/publico/"):
        return True
    return False


def verificar_token(token: str) -> dict:
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return payload
    except JWTError as e:
        logger.warning(f"Token inválido: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def middleware_auth(request: Request, call_next):
    if es_ruta_publica(request.url.path):
        return await call_next(request)

    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Se requiere token de autenticación",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = auth_header.split(" ")[1]
    payload = verificar_token(token)

    request.state.usuario_id  = payload.get("sub")
    request.state.usuario_rol = payload.get("rol", "")
    request.state.token       = token

    return await call_next(request)