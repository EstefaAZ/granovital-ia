# =============================================================
# app/services/auth_service.py
# Lógica de negocio del módulo de autenticación
# Trazabilidad: RF-01 | RNF-04 | RN-01
# =============================================================

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple
import requests
import random
import string
import httpx

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
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    UsuarioLoginResponse,
    RolResponse,
)
from app.services.email_service import EmailService
from app.services.verification_service import VerificationService
from app.services.google_oauth_service import GoogleOAuthService

logger = logging.getLogger(__name__)

# BUG-052 FIX: hash dummy pre-calculado para ejecutar siempre bcrypt
# y evitar timing attack que revele si un email existe o no.
DUMMY_HASH = "$2b$12$cc2GB.4iUTzZAvaOZsS/y.Zu4yMTwUHD1kRfQIApDmYqOe/jagPpi"


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

        sub = payload.get("sub")
        if not sub:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token de refresco inválido",
            )

        user_id = int(sub)
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
    # REGISTRO DE USUARIO
    # =============================================================

    async def registrar_usuario(self, datos: dict, ip_cliente: str) -> dict:
        """
        Registra un nuevo usuario con validación de email y creación de recursos según rol.
        """
        # Verificar que el email no exista
        usuario_existente = self.db.query(Usuario).filter(Usuario.correo == datos["correo"]).first()
        if usuario_existente:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El correo electrónico ya está registrado",
            )

        # Verificar código de verificación usando Redis
        verification_service = VerificationService()
        if not verification_service.verify_code(datos["correo"], datos.get("codigo_verificacion", "")):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Código de verificación incorrecto o expirado",
            )

        # Obtener rol
        rol = self.db.query(Rol).filter(Rol.nombre_rol == datos["rol"]).first()
        if not rol:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Rol inválido",
            )

        # Crear usuario
        nuevo_usuario = Usuario(
            nombre=datos["nombre"],
            apellido="",  # TODO: Separar nombre y apellido en frontend
            correo=datos["correo"],
            contrasena=hash_password(datos["contrasena"]),
            telefono=datos["telefono"],
            tipo_documento=datos["tipo_documento"],
            documento=datos["documento"],
            municipio=datos["municipio"],
            id_rol=rol.id_rol,
            estado_cuenta="activo",
            ultimo_acceso=datetime.now(timezone.utc),
            intentos_fallidos=0,
        )

        self.db.add(nuevo_usuario)
        self.db.commit()
        self.db.refresh(nuevo_usuario)

        # Crear recursos específicos según rol
        if datos["rol"] == "Caficultor":
            await self._crear_finca_caficultor(nuevo_usuario, datos)

        # Enviar email de bienvenida
        try:
            EmailService.enviar_bienvenida(nuevo_usuario.correo, nuevo_usuario.nombre)
        except Exception as e:
            logger.warning(f"No se pudo enviar email de bienvenida a {nuevo_usuario.correo}: {str(e)}")
            # No fallar el registro por esto

        # Generar tokens
        access_token = create_access_token(
            subject=str(nuevo_usuario.id_usuario),
            role=rol.nombre_rol,
            extra_data={"correo": nuevo_usuario.correo},
        )
        refresh_token = create_refresh_token(
            subject=str(nuevo_usuario.id_usuario)
        )

        logger.info(
            f"Usuario registrado exitosamente: id={nuevo_usuario.id_usuario}, "
            f"rol={datos['rol']}, email={nuevo_usuario.correo}, "
            f"municipio={nuevo_usuario.municipio}, ip={ip_cliente}"
        )

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "usuario": {
                "id_usuario": nuevo_usuario.id_usuario,
                "nombre": nuevo_usuario.nombre,
                "apellido": nuevo_usuario.apellido,
                "correo": nuevo_usuario.correo,
                "telefono": nuevo_usuario.telefono,
                "estado_cuenta": nuevo_usuario.estado_cuenta,
                "rol": {
                    "id_rol": rol.id_rol,
                    "nombre_rol": rol.nombre_rol,
                },
            },
        }

    def enviar_codigo_verificacion(self, correo: str) -> None:
        """
        Envía código de verificación por email y lo almacena en Redis.
        """
        try:
            # Generar y enviar código
            codigo = EmailService.enviar_codigo_verificacion(correo)

            # Almacenar código en Redis
            verification_service = VerificationService()
            verification_service.store_verification_code(correo, codigo)

            logger.info(f"Código de verificación enviado y almacenado para: {correo}")

        except Exception as e:
            logger.error(f"Error enviando código de verificación a {correo}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="No se pudo enviar el código de verificación. Inténtalo de nuevo.",
            )

    async def _crear_finca_caficultor(self, usuario: Usuario, datos: dict) -> None:
        """
        Crea un cultivo inicial para un nuevo Caficultor.
        Llama al servicio de cultivos via HTTP con token de servicio.
        """
        logger.info(f"Iniciando creación de cultivo para usuario {usuario.id_usuario}")

        try:
            # URL del servicio de cultivos (ajustar según docker-compose)
            cultivos_url = "http://cultivos:8000/api/v1/cultivos/cultivos"

            # Datos del cultivo
            cultivo_data = {
                "nombre_cultivo": datos.get("nombre_finca", f"Finca de {usuario.nombre} {usuario.apellido}"),
                "ubicacion": f"{datos.get('municipio', '')}, {datos.get('vereda', '')}".strip(", "),
                "area_hectareas": datos.get("area_cultivada"),
                "variedad_cafe": datos.get("variedad_principal"),
                "fecha_siembra": None,
                "observaciones": f"Cultivo creado automáticamente para usuario {usuario.id_usuario} durante registro"
            }

            logger.debug(f"Datos del cultivo a crear: {cultivo_data}")

            # Headers con token de servicio
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._get_service_token()}",
                "X-Service-Caller": "granovital_login",
                "X-User-Id": str(usuario.id_usuario)
            }

            logger.info(f"Llamando a cultivos API: {cultivos_url}")

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    cultivos_url,
                    json=cultivo_data,
                    headers=headers
                )

            logger.info(f"Respuesta de cultivos API: status={response.status_code}")

            if response.status_code == 201:
                logger.info(f"Cultivo creado exitosamente para usuario {usuario.id_usuario}")
                try:
                    response_data = response.json()
                    logger.debug(f"Respuesta completa: {response_data}")
                except:
                    logger.debug("No se pudo parsear respuesta JSON")
            elif response.status_code == 401:
                logger.error(f"Error de autenticación con cultivos API para usuario {usuario.id_usuario}")
                # No lanzamos excepción - el cultivo puede crearse manualmente
            elif response.status_code == 403:
                logger.error(f"Error de autorización con cultivos API para usuario {usuario.id_usuario}")
                # No lanzamos excepción - el cultivo puede crearse manualmente
            else:
                logger.warning(
                    f"No se pudo crear cultivo para usuario {usuario.id_usuario}: "
                    f"Status {response.status_code}, Response: {response.text[:500]}"
                )
                # No lanzamos excepción para no fallar el registro completo

        except httpx.TimeoutException:
            logger.error(f"Timeout llamando a cultivos API para usuario {usuario.id_usuario}")
        except httpx.ConnectError:
            logger.error(f"Error de conexión con cultivos API para usuario {usuario.id_usuario}")
        except Exception as e:
            logger.error(f"Error inesperado creando cultivo para usuario {usuario.id_usuario}: {str(e)}")
            # No lanzamos excepción para no fallar el registro

    def _get_service_token(self) -> str:
        """
        Genera un token de servicio para llamadas inter-módulo.
        Usa un usuario de servicio dedicado o crea un token con rol de servicio.

        Returns:
            Token JWT para autenticación de servicios
        """
        from app.core.security import create_access_token

        # TODO: Implementar usuario de servicio dedicado en la base de datos
        # Por ahora, simulamos un token de servicio con rol "Servicio"
        # En producción, esto debería ser un usuario especial con permisos limitados

        try:
            # Intentar obtener un usuario de servicio de la BD (si existe)
            usuario_servicio = self.db.query(Usuario).join(Rol).filter(
                Rol.nombre_rol == "Servicio"
            ).first()

            if usuario_servicio:
                logger.debug("Usando usuario de servicio dedicado")
                return create_access_token(
                    subject=str(usuario_servicio.id_usuario),
                    role="Servicio",
                    extra_data={"service_caller": "granovital_login"}
                )
            else:
                # Fallback: crear token con ID especial para servicios
                logger.debug("Usando token de servicio simulado")
                return create_access_token(
                    subject="service_granovital_login",
                    role="Servicio",
                    extra_data={
                        "service_caller": "granovital_login",
                        "service_purpose": "inter_module_call"
                    }
                )
        except Exception as e:
            logger.error(f"Error generando token de servicio: {str(e)}")
            # Fallback final
            return create_access_token(
                subject="service_fallback",
                role="Servicio"
            )

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

    # =============================================================
    # GOOGLE OAUTH
    # =============================================================

    def get_google_auth_url(self, state: Optional[str] = None) -> str:
        """
        Genera la URL de autorización de Google OAuth.

        Args:
            state: Estado opcional para prevenir CSRF

        Returns:
            URL de autorización de Google
        """
        oauth_service = GoogleOAuthService()
        return oauth_service.get_auth_url(state)

    async def handle_google_oauth_callback(self, code: str, ip_cliente: str) -> dict:
        """
        Maneja el callback de Google OAuth y registra/autentica al usuario.

        Args:
            code: Código de autorización de Google
            ip_cliente: IP del cliente

        Returns:
            Respuesta de login con tokens
        """
        oauth_service = GoogleOAuthService()

        try:
            # Obtener información del usuario desde Google
            user_profile = await oauth_service.get_user_profile(code)

            # Buscar usuario existente por google_id o email
            usuario = (
                self.db.query(Usuario)
                .options(joinedload(Usuario.rol))
                .filter(
                    (Usuario.google_id == user_profile["google_id"]) |
                    ((Usuario.correo == user_profile["email"]) & (Usuario.provider == "google"))
                )
                .first()
            )

            if usuario:
                # Usuario existente - actualizar información y login
                self._actualizar_usuario_google(usuario, user_profile)
                logger.info(f"Login OAuth Google para usuario existente: {usuario.correo}")
            else:
                # Usuario nuevo - registrar
                usuario = self._registrar_usuario_google(user_profile)
                logger.info(f"Registro OAuth Google para usuario nuevo: {usuario.correo}")

            # Actualizar último acceso
            self._registrar_login_exitoso(usuario, ip_cliente)

            # Generar tokens
            access_token = create_access_token(
                subject=str(usuario.id_usuario),
                role=usuario.rol.nombre_rol,
                extra_data={"correo": usuario.correo, "provider": "google"},
            )
            refresh_token = create_refresh_token(
                subject=str(usuario.id_usuario)
            )

            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "expires_in": settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
                "usuario": {
                    "id_usuario": usuario.id_usuario,
                    "nombre": usuario.nombre,
                    "apellido": usuario.apellido,
                    "correo": usuario.correo,
                    "telefono": usuario.telefono,
                    "estado_cuenta": usuario.estado_cuenta,
                    "provider": usuario.provider,
                    "avatar_url": usuario.avatar_url,
                    "rol": {
                        "id_rol": usuario.rol.id_rol,
                        "nombre_rol": usuario.rol.nombre_rol,
                    },
                },
            }

        except Exception as e:
            logger.error(f"Error en callback OAuth Google: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Error procesando autenticación con Google"
            )

    def _registrar_usuario_google(self, user_profile: dict) -> Usuario:
        """
        Registra un nuevo usuario desde Google OAuth.

        Args:
            user_profile: Perfil del usuario de Google

        Returns:
            Usuario creado
        """
        # Obtener rol por defecto (Consumidor)
        rol = self.db.query(Rol).filter(Rol.nombre_rol == "Consumidor").first()
        if not rol:
            # Si no existe, obtener el primer rol disponible
            rol = self.db.query(Rol).first()
            if not rol:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="No hay roles configurados en el sistema"
                )

        # Separar nombre y apellido
        nombre_completo = user_profile.get("name", "")
        partes_nombre = nombre_completo.split(" ", 1)
        nombre = partes_nombre[0] if partes_nombre else ""
        apellido = partes_nombre[1] if len(partes_nombre) > 1 else ""

        # Crear usuario
        nuevo_usuario = Usuario(
            nombre=nombre,
            apellido=apellido,
            correo=user_profile["email"],
            contrasena=hash_password(f"oauth_google_{user_profile['google_id']}"),  # Contraseña dummy
            telefono=None,
            google_id=user_profile["google_id"],
            provider="google",
            avatar_url=user_profile.get("picture"),
            id_rol=rol.id_rol,
            estado_cuenta="activo",
            ultimo_acceso=datetime.now(timezone.utc),
            intentos_fallidos=0,
        )

        self.db.add(nuevo_usuario)
        self.db.commit()
        self.db.refresh(nuevo_usuario)

        logger.info(f"Usuario registrado via Google OAuth: {nuevo_usuario.correo}")
        return nuevo_usuario

    def _actualizar_usuario_google(self, usuario: Usuario, user_profile: dict) -> None:
        """
        Actualiza la información de un usuario existente desde Google.

        Args:
            usuario: Usuario existente
            user_profile: Perfil actualizado de Google
        """
        # Actualizar información básica
        nombre_completo = user_profile.get("name", "")
        partes_nombre = nombre_completo.split(" ", 1)
        if partes_nombre:
            usuario.nombre = partes_nombre[0]
            if len(partes_nombre) > 1:
                usuario.apellido = partes_nombre[1]

        # Actualizar avatar si cambió
        if user_profile.get("picture") and user_profile["picture"] != usuario.avatar_url:
            usuario.avatar_url = user_profile["picture"]

        # Asegurar que google_id esté actualizado
        if not usuario.google_id:
            usuario.google_id = user_profile["google_id"]

        self.db.commit()