import logging
from fastapi import Request, status
from fastapi.responses import JSONResponse
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

# Headers CORS que se agregan manualmente a respuestas de error del middleware
CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Credentials": "true",
    "Access-Control-Allow-Methods": "GET, POST, PUT, PATCH, DELETE, OPTIONS",
    "Access-Control-Allow-Headers": "Authorization, Content-Type, Accept, X-Usuario-Nombre",
}


def es_ruta_publica(path: str) -> bool:
    if path in RUTAS_PUBLICAS:
        return True
    if path.startswith("/api/v1/trazabilidad/qr/publico/"):
        return True
    return False


def verificar_token(token: str) -> dict | None:
    try:
        return jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except JWTError as e:
        logger.warning(f"Token inválido: {e}")
        return None


async def middleware_auth(request: Request, call_next):
    # Dejar pasar preflight OPTIONS sin verificar token
    if request.method == "OPTIONS":
        return await call_next(request)

    if es_ruta_publica(request.url.path):
        return await call_next(request)

    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "Se requiere token de autenticación"},
            headers={
                **CORS_HEADERS,
                "WWW-Authenticate": "Bearer",
            },
        )

    token = auth_header.split(" ")[1]
    payload = verificar_token(token)

    if payload is None:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "Token inválido o expirado"},
            headers={
                **CORS_HEADERS,
                "WWW-Authenticate": "Bearer",
            },
        )

    request.state.usuario_id  = payload.get("sub")
    request.state.usuario_rol = payload.get("rol", "")
    request.state.token       = token

    return await call_next(request)