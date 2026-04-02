# =============================================================
# app/services/auth_service.py
# Lógica de negocio del módulo de autenticación
# Trazabilidad: RF-01 | RNF-04 | RN-01
# =============================================================

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple

from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException, status, Request

from app.core.security import (
    verify_password,
    hash_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.core.config import settings
from app.models.usuario import Usuario, Rol
from app.schemas.auth import LoginRequest, LoginResponse, UsuarioLoginResponse, RolResponse

logger = logging.getLogger(__name__)

# BUG-052 FIX: hash dummy pre-calculado para ejecutar siempre bcrypt
# y evitar timing attack que revele si un email existe o no.
DUMMY_HASH = "$2b$12$dummyhashfortimingatk.usedwhenusernotfound.x.x.x.x."


class AuthService:
    """
    Servicio de autenticación de GranoVital IA.

    Responsabilidades:
      - Validar credenciales contra tbl_usuario (RF-01)
      - Verificar estado de cuenta y bloqueos por intentos fallidos (RNF-04)
      - Emitir tokens JWT de acceso y refresco (RF-01)
      - Registrar auditoría de accesos (RNF-04, RNF-05)
      - Cambio seguro de contraseña
    """

    def __init__(self, db: Session):
        self.db = db

    # =============================================================
    # LOGIN PRINCIPAL
    # =============================================================

    def login(
        self,
        credentials: LoginRequest,
        ip_cliente: Optional[str] = None,
    ) -> LoginResponse:
        """
        Autentica al usuario con correo y contraseña.

        Flujo:
          1. Buscar usuario por correo en tbl_usuario
          2. Verificar estado de cuenta (activo/inactivo/suspendido)
          3. Verificar bloqueo por intentos fallidos
          4. Validar contraseña con bcrypt
          5. Actualizar último acceso y resetear contador de intentos
          6. Emitir access token + refresh token
          7. Registrar el acceso en auditoría

        Args:
            credentials: correo y contraseña del usuario
            ip_cliente:  IP de la solicitud para auditoría

        Returns:
            LoginResponse con tokens JWT e información del usuario

        Raises:
            HTTPException 401: credenciales inválidas
            HTTPException 403: cuenta suspendida o inactiva
            HTTPException 429: demasiados intentos fallidos
        """
        # Paso 1 — Buscar usuario con su rol cargado en un solo query
        usuario = (
            self.db.query(Usuario)
            .options(joinedload(Usuario.rol))
            .filter(Usuario.correo == credentials.correo.lower().strip())
            .first()
        )

        # Paso 2 y 3 — Verificaciones de estado
        # IMPORTANTE: siempre verificar la contraseña aunque el usuario
        # no exista (para evitar timing attacks que revelen correos válidos)
        password_valida = False
        if usuario:
            password_valida = verify_password(
                credentials.contrasena, usuario.contrasena
            )
        else:
            # BUG-052 FIX: ejecutar bcrypt aunque el usuario no exista
            # para que la respuesta tarde igual y no revele emails válidos
            verify_password(credentials.contrasena, DUMMY_HASH)

        # Paso 2 — Estado de cuenta (solo si el usuario existe)
        if usuario:
            self._verificar_estado_cuenta(usuario)
            self._verificar_bloqueo_por_intentos(usuario)

        # Paso 4 — Validar contraseña
        if not usuario or not password_valida:
            # Incrementar contador de intentos fallidos si el usuario existe
            if usuario:
                self._registrar_intento_fallido(usuario, ip_cliente)
            logger.warning(
                f"Login fallido para correo '{credentials.correo}' | IP: {ip_cliente}"
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Correo electrónico o contraseña incorrectos",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Paso 5 — Login exitoso: actualizar metadata del usuario
        self._registrar_login_exitoso(usuario, ip_cliente)

        # Paso 6 — Emitir tokens JWT
        access_token = create_access_token(
            subject=str(usuario.id_usuario),
            role=usuario.rol.nombre_rol,
            extra_data={"correo": usuario.correo},
        )
        refresh_token = create_refresh_token(
            subject=str(usuario.id_usuario)
        )

        logger.info(
            f"Login exitoso: usuario_id={usuario.id_usuario} "
            f"rol='{usuario.rol.nombre_rol}' | IP: {ip_cliente}"
        )

        # Paso 7 — Construir y retornar respuesta
        return LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            usuario=UsuarioLoginResponse(
                id_usuario=usuario.id_usuario,
                nombre=usuario.nombre,
                apellido=usuario.apellido,
                correo=usuario.correo,
                telefono=usuario.telefono,
                estado_cuenta=usuario.estado_cuenta,
                ultimo_acceso=usuario.ultimo_acceso,
                rol=RolResponse(
                    id_rol=usuario.rol.id_rol,
                    nombre_rol=usuario.rol.nombre_rol,
                    descripcion=usuario.rol.descripcion,
                ),
            ),
        )

    # =============================================================
    # REFRESH TOKEN
    # =============================================================

    def refresh_access_token(self, refresh_token: str) -> dict:
        """
        Genera un nuevo access token a partir de un refresh token válido.
        No requiere que el usuario vuelva a ingresar su contraseña.

        Args:
            refresh_token: token de refresco emitido en el login

        Returns:
            dict con nuevo access_token y expires_in

        Raises:
            HTTPException 401: refresh token inválido o expirado
        """
        payload = decode_token(refresh_token)

        # Verificar que sea un refresh token (no access)
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token de refresco inválido",
            )

        user_id = int(payload.get("sub"))
        usuario = (
            self.db.query(Usuario)
            .options(joinedload(Usuario.rol))
            .filter(Usuario.id_usuario == user_id)
            .first()
        )

        if not usuario or not usuario.esta_activo:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Usuario no encontrado o cuenta inactiva",
            )

        new_access_token = create_access_token(
            subject=str(usuario.id_usuario),
            role=usuario.rol.nombre_rol,
            extra_data={"correo": usuario.correo},
        )

        return {
            "access_token": new_access_token,
            "token_type": "bearer",
            "expires_in": settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        }

    # =============================================================
    # CAMBIO DE CONTRASEÑA
    # =============================================================

    def cambiar_password(
        self,
        usuario_id: int,
        contrasena_actual: str,
        contrasena_nueva: str,
    ) -> None:
        """
        Cambia la contraseña del usuario después de verificar la actual.
        Implementa RNF-04 (seguridad de la información).

        Args:
            usuario_id:       ID del usuario autenticado
            contrasena_actual: contraseña actual para confirmar identidad
            contrasena_nueva:  nueva contraseña a establecer

        Raises:
            HTTPException 400: contraseña actual incorrecta
            HTTPException 404: usuario no encontrado
        """
        usuario = self.db.query(Usuario).filter(
            Usuario.id_usuario == usuario_id
        ).first()

        if not usuario:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado",
            )

        if not verify_password(contrasena_actual, usuario.contrasena):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La contraseña actual es incorrecta",
            )

        usuario.contrasena = hash_password(contrasena_nueva)
        self.db.commit()

        logger.info(f"Contraseña actualizada para usuario_id={usuario_id}")

    # =============================================================
    # MÉTODOS PRIVADOS DE SOPORTE
    # =============================================================

    def _verificar_estado_cuenta(self, usuario: Usuario) -> None:
        """Verifica que la cuenta no esté inactiva o suspendida."""
        if usuario.estado_cuenta == "inactivo":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Esta cuenta ha sido desactivada. Contacte al administrador.",
            )
        if usuario.estado_cuenta == "suspendido":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "Esta cuenta ha sido suspendida por múltiples intentos de acceso fallidos. "
                    "Contacte al administrador del sistema."
                ),
            )

    def _verificar_bloqueo_por_intentos(self, usuario: Usuario) -> None:
        """
        Bloquea el acceso si el usuario superó el máximo de intentos fallidos.
        Implementa protección contra ataques de fuerza bruta (RNF-04).
        """
        if usuario.intentos_fallidos >= settings.MAX_LOGIN_ATTEMPTS:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=(
                    f"Cuenta bloqueada temporalmente por {settings.MAX_LOGIN_ATTEMPTS} intentos fallidos. "
                    f"Contacte al administrador o espere {settings.LOGIN_LOCKOUT_MINUTES} minutos."
                ),
            )

    def _registrar_intento_fallido(
        self, usuario: Usuario, ip_cliente: Optional[str]
    ) -> None:
        """
        Incrementa el contador de intentos fallidos.
        Si supera el máximo, suspende la cuenta automáticamente.
        """
        usuario.intentos_fallidos += 1

        if usuario.intentos_fallidos >= settings.MAX_LOGIN_ATTEMPTS:
            usuario.estado_cuenta = "suspendido"
            logger.warning(
                f"Cuenta suspendida por intentos fallidos: "
                f"usuario_id={usuario.id_usuario} | IP: {ip_cliente}"
            )

        self.db.commit()

    def _registrar_login_exitoso(
        self, usuario: Usuario, ip_cliente: Optional[str]
    ) -> None:
        """
        Actualiza el último acceso y resetea el contador de intentos
        fallidos al confirmar login exitoso.
        """
        usuario.ultimo_acceso = datetime.now(timezone.utc)
        usuario.intentos_fallidos = 0
        self.db.commit()
