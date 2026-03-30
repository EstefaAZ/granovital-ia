# =============================================================
# tests/test_auth.py
# Pruebas unitarias e integración del módulo de autenticación
# Trazabilidad: RF-01 | RNF-04 | Test Plan del proyecto
# =============================================================

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.core.security import hash_password, verify_password, create_access_token, decode_token
from app.models.usuario import Usuario, Rol
from app.schemas.auth import LoginRequest
from app.services.auth_service import AuthService

client = TestClient(app)


# =============================================================
# FIXTURES
# =============================================================

@pytest.fixture
def rol_caficultor():
    """Rol de Caficultor para pruebas."""
    rol = MagicMock(spec=Rol)
    rol.id_rol = 2
    rol.nombre_rol = "Caficultor"
    rol.descripcion = "Gestión del cultivo e IA fitosanitaria"
    return rol


@pytest.fixture
def usuario_activo(rol_caficultor):
    """Usuario activo con contraseña hasheada para pruebas."""
    usuario = MagicMock(spec=Usuario)
    usuario.id_usuario = 1
    usuario.nombre = "Carlos"
    usuario.apellido = "Restrepo"
    usuario.correo = "caficultor@granovital.co"
    usuario.contrasena = hash_password("password123")
    usuario.telefono = "3001234567"
    usuario.estado_cuenta = "activo"
    usuario.intentos_fallidos = 0
    usuario.ultimo_acceso = None
    usuario.esta_activo = True
    usuario.rol = rol_caficultor
    return usuario


@pytest.fixture
def usuario_suspendido(rol_caficultor):
    """Usuario con cuenta suspendida para pruebas."""
    usuario = MagicMock(spec=Usuario)
    usuario.id_usuario = 2
    usuario.correo = "bloqueado@granovital.co"
    usuario.contrasena = hash_password("password123")
    usuario.estado_cuenta = "suspendido"
    usuario.intentos_fallidos = 5
    usuario.esta_activo = False
    usuario.rol = rol_caficultor
    return usuario


@pytest.fixture
def db_mock():
    """Sesión de base de datos simulada."""
    return MagicMock(spec=Session)


# =============================================================
# PRUEBAS DE SEGURIDAD — bcrypt (RNF-04)
# =============================================================

class TestBcrypt:
    """Verifica que el hash y verificación de contraseñas funcionen correctamente."""

    def test_hash_genera_cadena_diferente(self):
        """El hash debe ser diferente a la contraseña original."""
        plain = "mi_password_123"
        hashed = hash_password(plain)
        assert hashed != plain

    def test_hash_tiene_longitud_bcrypt(self):
        """BUG-030 FIX: bcrypt con passlib puede tener 59-60 chars según versión.
        Verificar el prefijo $2b$ es más robusto que verificar longitud exacta.
        """
        hashed = hash_password("cualquier_password")
        assert hashed.startswith("$2b$"), f"Hash no es bcrypt válido: {hashed[:10]}"
        assert len(hashed) >= 59, f"Hash demasiado corto: {len(hashed)} chars"

    def test_verify_password_correcto(self):
        """verify_password retorna True con la contraseña correcta."""
        plain = "password_correcto"
        hashed = hash_password(plain)
        assert verify_password(plain, hashed) is True

    def test_verify_password_incorrecto(self):
        """verify_password retorna False con contraseña incorrecta."""
        hashed = hash_password("password_real")
        assert verify_password("password_falso", hashed) is False

    def test_mismo_password_genera_hashes_distintos(self):
        """bcrypt genera salt aleatorio: misma contraseña produce hashes diferentes."""
        plain = "mismo_password"
        hash1 = hash_password(plain)
        hash2 = hash_password(plain)
        assert hash1 != hash2
        # Pero ambos verifican correctamente
        assert verify_password(plain, hash1) is True
        assert verify_password(plain, hash2) is True


# =============================================================
# PRUEBAS DE TOKENS JWT (RF-01, RNF-04)
# =============================================================

class TestJWT:
    """Verifica la generación y validación de tokens JWT."""

    def test_create_access_token_valido(self):
        """El token se decodifica correctamente con el sujeto y rol."""
        token = create_access_token(subject="42", role="Caficultor")
        payload = decode_token(token)
        assert payload["sub"] == "42"
        assert payload["role"] == "Caficultor"
        assert payload["type"] == "access"

    def test_token_con_datos_extra(self):
        """El token puede incluir datos adicionales."""
        token = create_access_token(
            subject="1",
            role="Administrador",
            extra_data={"correo": "admin@test.co"},
        )
        payload = decode_token(token)
        assert payload["correo"] == "admin@test.co"

    def test_token_invalido_lanza_excepcion(self):
        """Un token malformado debe lanzar HTTPException 401."""
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            decode_token("token.falso.invalido")
        assert exc_info.value.status_code == 401


# =============================================================
# PRUEBAS DEL SERVICIO DE AUTENTICACIÓN (RF-01)
# =============================================================

class TestAuthService:
    """Pruebas de la lógica de negocio del AuthService."""

    def test_login_exitoso(self, db_mock, usuario_activo):
        """Login con credenciales correctas retorna tokens y datos del usuario."""
        # Configurar mock de base de datos
        query_mock = MagicMock()
        query_mock.options.return_value.filter.return_value.first.return_value = usuario_activo
        db_mock.query.return_value = query_mock

        service = AuthService(db_mock)
        credentials = LoginRequest(
            correo="caficultor@granovital.co",
            contrasena="password123",
        )

        response = service.login(credentials, ip_cliente="127.0.0.1")

        assert response.access_token is not None
        assert response.refresh_token is not None
        assert response.token_type == "bearer"
        assert response.usuario.correo == "caficultor@granovital.co"
        assert response.usuario.rol.nombre_rol == "Caficultor"

    def test_login_password_incorrecto_lanza_401(self, db_mock, usuario_activo):
        """Contraseña incorrecta debe retornar HTTP 401."""
        from fastapi import HTTPException

        query_mock = MagicMock()
        query_mock.options.return_value.filter.return_value.first.return_value = usuario_activo
        db_mock.query.return_value = query_mock

        service = AuthService(db_mock)
        credentials = LoginRequest(
            correo="caficultor@granovital.co",
            contrasena="password_incorrecto",
        )

        with pytest.raises(HTTPException) as exc_info:
            service.login(credentials)
        assert exc_info.value.status_code == 401

    def test_login_usuario_no_existe_lanza_401(self, db_mock):
        """Correo inexistente debe retornar HTTP 401 (sin revelar que no existe)."""
        from fastapi import HTTPException

        query_mock = MagicMock()
        query_mock.options.return_value.filter.return_value.first.return_value = None
        db_mock.query.return_value = query_mock

        service = AuthService(db_mock)
        credentials = LoginRequest(
            correo="noexiste@granovital.co",
            contrasena="cualquier_password",
        )

        with pytest.raises(HTTPException) as exc_info:
            service.login(credentials)
        # Siempre debe ser 401 (no revelar si el correo existe o no)
        assert exc_info.value.status_code == 401

    def test_login_cuenta_suspendida_lanza_403(self, db_mock, usuario_suspendido):
        """Cuenta suspendida debe retornar HTTP 403."""
        from fastapi import HTTPException

        query_mock = MagicMock()
        query_mock.options.return_value.filter.return_value.first.return_value = usuario_suspendido
        db_mock.query.return_value = query_mock

        service = AuthService(db_mock)
        credentials = LoginRequest(
            correo="bloqueado@granovital.co",
            contrasena="password123",
        )

        with pytest.raises(HTTPException) as exc_info:
            service.login(credentials)
        assert exc_info.value.status_code == 403

    def test_login_incrementa_intentos_fallidos(self, db_mock, usuario_activo):
        """Tras un fallo, el contador de intentos debe incrementarse."""
        from fastapi import HTTPException

        query_mock = MagicMock()
        query_mock.options.return_value.filter.return_value.first.return_value = usuario_activo
        db_mock.query.return_value = query_mock

        service = AuthService(db_mock)
        credentials = LoginRequest(
            correo="caficultor@granovital.co",
            contrasena="password_malo",
        )

        intentos_iniciales = usuario_activo.intentos_fallidos

        with pytest.raises(HTTPException):
            service.login(credentials)

        assert usuario_activo.intentos_fallidos == intentos_iniciales + 1

    def test_login_exitoso_resetea_intentos(self, db_mock, usuario_activo):
        """Login exitoso debe resetear el contador de intentos fallidos a 0."""
        usuario_activo.intentos_fallidos = 3  # Tenía intentos previos

        query_mock = MagicMock()
        query_mock.options.return_value.filter.return_value.first.return_value = usuario_activo
        db_mock.query.return_value = query_mock

        service = AuthService(db_mock)
        credentials = LoginRequest(
            correo="caficultor@granovital.co",
            contrasena="password123",
        )

        service.login(credentials)
        assert usuario_activo.intentos_fallidos == 0


# =============================================================
# PRUEBAS DE ENDPOINTS HTTP (Integración)
# =============================================================

class TestLoginEndpoint:
    """Pruebas de integración del endpoint POST /api/v1/auth/login."""

    def test_login_datos_invalidos_retorna_422(self):
        """Datos malformados deben retornar HTTP 422 (Unprocessable Entity)."""
        response = client.post("/api/v1/auth/login", json={
            "correo": "correo_invalido_sin_arroba",
            "contrasena": "abc",
        })
        assert response.status_code == 422

    def test_login_sin_cuerpo_retorna_422(self):
        """Solicitud sin cuerpo debe retornar HTTP 422."""
        response = client.post("/api/v1/auth/login", json={})
        assert response.status_code == 422

    def test_health_check_disponible(self):
        """El endpoint /health debe estar siempre disponible (RNF-03)."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["estado"] == "saludable"

    def test_endpoint_me_sin_token_retorna_403(self):
        """Acceder a /me sin token debe retornar error de autenticación."""
        response = client.get("/api/v1/auth/me")
        assert response.status_code in [401, 403]
