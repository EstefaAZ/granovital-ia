# =============================================================
# app/services/verification_service.py
# Servicio para gestión de códigos de verificación
# =============================================================

import logging
import redis
import json
from typing import Optional
from datetime import datetime, timedelta

from app.core.config import settings

logger = logging.getLogger(__name__)


class VerificationService:
    """
    Servicio para gestión de códigos de verificación usando Redis.
    """

    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.redis_available: bool = False

        try:
            self.redis_client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                password=settings.REDIS_PASSWORD or None,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            # Verificar conexión
            self.redis_client.ping()
            self.redis_available = True
            logger.info("Conexión a Redis establecida correctamente")
        except Exception as e:
            logger.error(f"Error conectando a Redis: {str(e)}")
            self.redis_available = False
            self.redis_client = None

    def _get_key(self, email: str) -> str:
        """Genera la clave Redis para un email."""
        return f"verification:{email.lower().strip()}"

    def store_verification_code(self, email: str, code: str) -> None:
        """
        Almacena un código de verificación con expiración.

        Args:
            email: Correo electrónico
            code: Código de verificación
        """
        if not self.redis_available:
            logger.error("Redis no disponible, no se puede almacenar código de verificación")
            raise Exception("Servicio de verificación no disponible")

        key = self._get_key(email)
        data = {
            "code": code,
            "created_at": datetime.now().isoformat(),
            "attempts": 0
        }

        try:
            if self.redis_client is None:
                raise Exception("Servicio de verificación no disponible")
            redis_client = self.redis_client
            redis_client.setex(
                key,
                timedelta(minutes=settings.EMAIL_VERIFICATION_CODE_EXPIRE_MINUTES),
                json.dumps(data)
            )
            logger.info(f"Código de verificación almacenado para: {email}")
        except Exception as e:
            logger.error(f"Error almacenando código de verificación para {email}: {str(e)}")
            raise

    def verify_code(self, email: str, code: str) -> bool:
        """
        Verifica si un código es válido para un email.

        Args:
            email: Correo electrónico
            code: Código a verificar

        Returns:
            True si el código es válido, False en caso contrario
        """
        if not self.redis_available:
            logger.warning("Redis no disponible, no se puede verificar código")
            return False

        key = self._get_key(email)

        try:
            if self.redis_client is None:
                raise Exception("Servicio de verificación no disponible")
            redis_client = self.redis_client
            data_str = redis_client.get(key)
            if not data_str:
                logger.warning(f"Código expirado o no encontrado para: {email}")
                return False

            # Asegurarse de que data_str sea una cadena
            if isinstance(data_str, bytes):
                data_str = data_str.decode('utf-8')
            elif not isinstance(data_str, str):
                data_str = str(data_str)

            try:
                data = json.loads(data_str)
            except json.JSONDecodeError as e:
                logger.error(f"Error decodificando JSON para {email} en verify_code: {str(e)}, data_str: {data_str}")
                return False

            # Verificar si el código coincide
            if data["code"] != code:
                # Incrementar contador de intentos
                data["attempts"] = data.get("attempts", 0) + 1

                # Si hay demasiados intentos fallidos, eliminar el código
                if data["attempts"] >= 3:
                    redis_client.delete(key)
                    logger.warning(f"Demasiados intentos fallidos para {email}, código eliminado")
                    return False

                # Guardar el contador actualizado
                redis_client.setex(
                    key,
                    timedelta(minutes=settings.EMAIL_VERIFICATION_CODE_EXPIRE_MINUTES),
                    json.dumps(data)
                )

                logger.warning(f"Código incorrecto para {email}, intento {data['attempts']}/3")
                return False

            # Código válido, eliminarlo para evitar reutilización
            redis_client.delete(key)
            logger.info(f"Código verificado correctamente para: {email}")
            return True

        except Exception as e:
            logger.error(f"Error verificando código para {email}: {str(e)}")
            return False

    def get_verification_status(self, email: str) -> Optional[dict]:
        """
        Obtiene el estado actual de verificación para un email.

        Args:
            email: Correo electrónico

        Returns:
            Dict con información del código o None si no existe
        """
        if not self.redis_available:
            logger.warning("Redis no disponible, no se puede obtener estado de verificación")
            return None

        key = self._get_key(email)

        try:
            if self.redis_client is None:
                raise Exception("Servicio de verificación no disponible")
            redis_client = self.redis_client
            data_str = redis_client.get(key)
            if not data_str:
                return None

            # Asegurarse de que data_str sea una cadena
            if isinstance(data_str, bytes):
                data_str = data_str.decode('utf-8')
            elif not isinstance(data_str, str):
                data_str = str(data_str)

            try:
                data = json.loads(data_str)
            except json.JSONDecodeError as e:
                logger.error(f"Error decodificando JSON para {email} en get_verification_status: {str(e)}, data_str: {data_str}")
                return None

            return {
                "exists": True,
                "created_at": data.get("created_at"),
                "attempts": data.get("attempts", 0),
                "expires_in_seconds": redis_client.ttl(key)
            }
        except Exception as e:
            logger.error(f"Error obteniendo estado de verificación para {email}: {str(e)}")
            return None

    def delete_verification_code(self, email: str) -> None:
        """
        Elimina un código de verificación.

        Args:
            email: Correo electrónico
        """
        if not self.redis_available:
            logger.warning("Redis no disponible, no se puede eliminar código de verificación")
            return

        key = self._get_key(email)

        try:
            if self.redis_client is None:
                raise Exception("Servicio de verificación no disponible")
            redis_client = self.redis_client
            redis_client.delete(key)
            logger.info(f"Código de verificación eliminado para: {email}")
        except Exception as e:
            logger.error(f"Error eliminando código de verificación para {email}: {str(e)}")