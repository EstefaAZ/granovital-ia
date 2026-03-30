# =============================================================
# app/api/v1/auth.py
# Router FastAPI — Endpoints de autenticación
# Trazabilidad: RF-01 | RNF-01, RNF-04 | RN-01
# =============================================================

import logging
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import (
    get_current_user_id,
    get_current_user_payload,
)
from app.services.auth_service import AuthService
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    RefreshTokenRequest,
    RefreshTokenResponse,
    CambiarPasswordRequest,
    MensajeResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/auth",
    tags=["Autenticación"],
)


def get_client_ip(request: Request) -> str:
    """Extrae la IP real del cliente considerando proxies inversos (Nginx)."""
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "desconocida"


# =============================================================
# POST /api/v1/auth/login
# =============================================================

@router.post(
    "/login",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    summary="Iniciar sesión",
    description=(
        "Autentica al usuario con correo y contraseña según su rol. "
        "Implementa RF-01. Retorna tokens JWT de acceso y refresco. "
        "Bloquea la cuenta tras múltiples intentos fallidos (RNF-04)."
    ),
    responses={
        200: {"description": "Login exitoso — retorna tokens JWT y datos del usuario"},
        401: {"description": "Credenciales incorrectas"},
        403: {"description": "Cuenta suspendida o inactiva"},
        422: {"description": "Datos de entrada inválidos (correo mal formado, contraseña vacía)"},
        429: {"description": "Cuenta bloqueada por demasiados intentos fallidos"},
    },
)
def login(
    credentials: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> LoginResponse:
    """
    **RF-01 — Autenticación de usuarios**

    Permite el ingreso al sistema mediante correo y contraseña.
    El rol del usuario queda codificado en el token JWT para
    ser usado por el middleware RBAC en cada solicitud posterior (RN-01).

    - La contraseña se compara contra el hash bcrypt almacenado en tbl_usuario.
    - Tras 5 intentos fallidos consecutivos, la cuenta queda suspendida.
    - El access token expira en 60 minutos (configurable en .env).
    - El refresh token expira en 7 días.
    """
    ip = get_client_ip(request)
    service = AuthService(db)
    return service.login(credentials, ip_cliente=ip)


# =============================================================
# POST /api/v1/auth/refresh
# =============================================================

@router.post(
    "/refresh",
    response_model=RefreshTokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Renovar token de acceso",
    description="Genera un nuevo access token usando el refresh token. No requiere contraseña.",
    responses={
        200: {"description": "Nuevo access token generado"},
        401: {"description": "Refresh token inválido o expirado"},
    },
)
def refresh_token(
    body: RefreshTokenRequest,
    db: Session = Depends(get_db),
) -> RefreshTokenResponse:
    """
    Permite renovar el access token sin que el usuario vuelva a
    ingresar su contraseña, mientras el refresh token sea válido.
    """
    service = AuthService(db)
    result = service.refresh_access_token(body.refresh_token)
    return RefreshTokenResponse(**result)


# =============================================================
# POST /api/v1/auth/logout
# =============================================================

@router.post(
    "/logout",
    response_model=MensajeResponse,
    status_code=status.HTTP_200_OK,
    summary="Cerrar sesión",
    description="Invalida la sesión actual del usuario. El cliente debe eliminar los tokens localmente.",
)
def logout(
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
    payload: dict = Depends(get_current_user_payload),
) -> MensajeResponse:
    """
    BUG-044 FIX: Agrega el token a la blacklist de Redis con TTL
    igual al tiempo restante de expiración. Si Redis no está
    disponible, el logout funciona igual (solo client-side).
    """
    user_id = payload.get("sub")
    jti     = payload.get("jti") or payload.get("sub", "")
    exp     = payload.get("exp", 0)

    if _redis:
        try:
            import time
            ttl = max(int(exp - time.time()), 1)
            _redis.setex(f"blacklist:{jti}", ttl, "1")
            logger.info(f"Token añadido a blacklist Redis: jti={jti} ttl={ttl}s")
        except Exception as e:
            logger.warning(f"No se pudo añadir token a blacklist Redis: {e}")

    logger.info(f"Logout: usuario_id={user_id}")
    return MensajeResponse(
        mensaje="Sesión cerrada correctamente.",
        exitoso=True,
    )


# =============================================================
# POST /api/v1/auth/change-password
# =============================================================

@router.post(
    "/change-password",
    response_model=MensajeResponse,
    status_code=status.HTTP_200_OK,
    summary="Cambiar contraseña",
    description="Permite al usuario autenticado cambiar su contraseña. Requiere la contraseña actual (RNF-04).",
    responses={
        200: {"description": "Contraseña actualizada correctamente"},
        400: {"description": "Contraseña actual incorrecta o nueva contraseña inválida"},
        401: {"description": "No autenticado"},
    },
)
def change_password(
    body: CambiarPasswordRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> MensajeResponse:
    """
    Cambio seguro de contraseña. Requiere autenticación activa y
    confirmación de la contraseña actual para prevenir cambios no
    autorizados si alguien accede a una sesión abierta (RNF-04).
    """
    service = AuthService(db)
    service.cambiar_password(
        usuario_id=user_id,
        contrasena_actual=body.contrasena_actual,
        contrasena_nueva=body.contrasena_nueva,
    )
    return MensajeResponse(
        mensaje="Contraseña actualizada correctamente.",
        exitoso=True,
    )


# =============================================================
# GET /api/v1/auth/me
# =============================================================

@router.get(
    "/me",
    status_code=status.HTTP_200_OK,
    summary="Información del usuario autenticado",
    description="Retorna los datos del usuario actual extraídos del token JWT. Útil para el frontend.",
)
def get_me(
    payload: dict = Depends(get_current_user_payload),
    db: Session = Depends(get_db),
) -> dict:
    """
    Endpoint de verificación de sesión. El frontend puede llamarlo
    al iniciar para saber si el token guardado sigue siendo válido
    y obtener los datos básicos del usuario (RF-02).
    """
    from app.models.usuario import Usuario
    from sqlalchemy.orm import joinedload

    user_id = int(payload.get("sub"))
    usuario = (
        db.query(Usuario)
        .options(joinedload(Usuario.rol))
        .filter(Usuario.id_usuario == user_id)
        .first()
    )

    if not usuario:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    return {
        "id_usuario":    usuario.id_usuario,
        "nombre":        usuario.nombre,
        "apellido":      usuario.apellido,
        "correo":        usuario.correo,
        "estado_cuenta": usuario.estado_cuenta,
        "ultimo_acceso": usuario.ultimo_acceso,
        "rol": {
            "id_rol":     usuario.rol.id_rol,
            "nombre_rol": usuario.rol.nombre_rol,
        },
    }
