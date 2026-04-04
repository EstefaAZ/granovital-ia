# =============================================================
# app/services/google_oauth_service.py
# Servicio de autenticación OAuth con Google
# =============================================================

import importlib
import logging
from typing import Optional, Dict, Any
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class GoogleOAuthService:
    """
    Servicio para autenticación OAuth con Google.
    """

    GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/auth"
    GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
    GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

    def __init__(self):
        self.client_id = settings.GOOGLE_CLIENT_ID
        self.client_secret = settings.GOOGLE_CLIENT_SECRET.get_secret_value()
        self.redirect_uri = settings.GOOGLE_REDIRECT_URI
        self.enabled = settings.GOOGLE_OAUTH_ENABLED

    def is_enabled(self) -> bool:
        """Verifica si Google OAuth está habilitado."""
        return self.enabled and bool(self.client_id) and bool(self.client_secret)

    def get_auth_url(self, state: Optional[str] = None) -> str:
        """
        Genera la URL de autorización de Google OAuth.

        Args:
            state: Estado opcional para prevenir CSRF

        Returns:
            URL de autorización de Google
        """
        if not self.is_enabled():
            raise ValueError("Google OAuth no está configurado")

        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": "openid email profile",
            "response_type": "code",
            "access_type": "offline",
            "prompt": "consent"
        }

        if state:
            params["state"] = state

        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"{self.GOOGLE_AUTH_URL}?{query_string}"

    async def exchange_code_for_token(self, code: str) -> Dict[str, Any]:
        """
        Intercambia el código de autorización por tokens de acceso.

        Args:
            code: Código de autorización recibido de Google

        Returns:
            Diccionario con tokens de acceso
        """
        if not self.is_enabled():
            raise ValueError("Google OAuth no está configurado")

        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": self.redirect_uri
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(self.GOOGLE_TOKEN_URL, data=data)
            response.raise_for_status()
            return response.json()

    async def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """
        Obtiene información del usuario usando el token de acceso.

        Args:
            access_token: Token de acceso de Google

        Returns:
            Información del usuario de Google
        """
        headers = {"Authorization": f"Bearer {access_token}"}

        async with httpx.AsyncClient() as client:
            response = await client.get(self.GOOGLE_USERINFO_URL, headers=headers)
            response.raise_for_status()
            return response.json()

    def verify_id_token(self, id_token_str: str) -> Dict[str, Any]:
        """
        Verifica y decodifica el ID token de Google.

        Args:
            id_token_str: ID token de Google

        Returns:
            Payload decodificado del token
        """
        if not self.is_enabled():
            raise ValueError("Google OAuth no está configurado")

        try:
            google_requests = importlib.import_module("google.auth.transport.requests")
            id_token = importlib.import_module("google.oauth2.id_token")
        except ImportError as exc:
            raise RuntimeError(
                "google-auth no está instalado. Instala google-auth y google-auth-oauthlib."
            ) from exc

        try:
            # Verificar el token usando la librería de Google
            id_info = id_token.verify_oauth2_token(
                id_token_str,
                google_requests.Request(),
                self.client_id
            )
            return id_info
        except Exception as e:
            logger.error(f"Error verificando ID token de Google: {str(e)}")
            raise ValueError("Token de Google inválido")

    async def get_user_profile(self, code: str) -> Dict[str, Any]:
        """
        Obtiene el perfil completo del usuario desde Google.

        Args:
            code: Código de autorización

        Returns:
            Perfil del usuario con información de Google
        """
        # Intercambiar código por tokens
        token_response = await self.exchange_code_for_token(code)

        # Obtener información del usuario
        user_info = await self.get_user_info(token_response["access_token"])

        # Verificar ID token si está presente
        if "id_token" in token_response:
            id_info = self.verify_id_token(token_response["id_token"])
            user_info.update(id_info)

        return {
            "google_id": user_info.get("id"),
            "email": user_info.get("email"),
            "email_verified": user_info.get("email_verified", False),
            "name": user_info.get("name"),
            "given_name": user_info.get("given_name"),
            "family_name": user_info.get("family_name"),
            "picture": user_info.get("picture"),
            "locale": user_info.get("locale"),
            "access_token": token_response.get("access_token"),
            "refresh_token": token_response.get("refresh_token"),
            "expires_in": token_response.get("expires_in")
        }