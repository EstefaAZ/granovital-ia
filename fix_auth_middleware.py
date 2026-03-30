#!/usr/bin/env python3
# =============================================================
# GranoVital IA — Parche puntual: BUG-006 + BUG-012 completo
# Archivo: Backend/api_gateway/app/middleware/auth.py
#
# Corrige los 2 JSONResponse que aún usaban CORS_HEADERS (variable
# eliminada) en lugar de la nueva función _cors_headers(request).
# También incluye el fix BUG-006 (payload "rol" -> "role").
# =============================================================

import os, sys, shutil
from pathlib import Path
from datetime import datetime

BASE = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(r"C:\\GranoVital-IA")

target = BASE / "Backend" / "api_gateway" / "app" / "middleware" / "auth.py"

if not target.exists():
    print(f"❌ No se encontró: {target}")
    sys.exit(1)

# Backup
bak = target.with_suffix(f".py.bak_{datetime.now().strftime('%H%M%S')}")
shutil.copy2(target, bak)
print(f"📦 Backup: {bak.name}")

NEW_CONTENT = "import logging\nfrom fastapi import Request, status\nfrom fastapi.responses import JSONResponse\nfrom jose import JWTError, jwt\n\nfrom app.core.config import settings\n\nlogger = logging.getLogger(__name__)\n\nRUTAS_PUBLICAS = {\n    \"/\",\n    \"/health\",\n    \"/docs\",\n    \"/redoc\",\n    \"/openapi.json\",\n    \"/api/v1/auth/login\",\n    \"/api/v1/auth/refresh\",\n}\n\n# Headers CORS que se agregan manualmente a respuestas de error del middleware.\n# BUG-012 FIX: No usar \"*\" cuando allow_credentials=True \u2014 los navegadores lo rechazan.\n# La funci\u00f3n _cors_headers() lee el Origin del request y lo refleja expl\u00edcitamente.\n_ALLOWED_ORIGINS_SET = set(settings.ALLOWED_ORIGINS.split(\",\"))\n\n\ndef _cors_headers(request: Request) -> dict:\n    \"\"\"Retorna headers CORS seguros para respuestas de error del middleware.\"\"\"\n    origin = request.headers.get(\"origin\", \"\")\n    allow_origin = origin if origin in _ALLOWED_ORIGINS_SET else (\n        list(_ALLOWED_ORIGINS_SET)[0] if _ALLOWED_ORIGINS_SET else \"*\"\n    )\n    return {\n        \"Access-Control-Allow-Origin\": allow_origin,\n        \"Access-Control-Allow-Credentials\": \"true\",\n        \"Access-Control-Allow-Methods\": \"GET, POST, PUT, PATCH, DELETE, OPTIONS\",\n        \"Access-Control-Allow-Headers\": \"Authorization, Content-Type, Accept, X-Usuario-Nombre\",\n    }\n\n\ndef es_ruta_publica(path: str) -> bool:\n    if path in RUTAS_PUBLICAS:\n        return True\n    if path.startswith(\"/api/v1/trazabilidad/qr/publico/\"):\n        return True\n    return False\n\n\ndef verificar_token(token: str) -> dict | None:\n    try:\n        return jwt.decode(\n            token,\n            settings.JWT_SECRET_KEY.get_secret_value(),\n            algorithms=[settings.JWT_ALGORITHM],\n        )\n    except JWTError as e:\n        logger.warning(f\"Token inv\u00e1lido: {e}\")\n        return None\n\n\nasync def middleware_auth(request: Request, call_next):\n    # Dejar pasar preflight OPTIONS sin verificar token\n    if request.method == \"OPTIONS\":\n        return await call_next(request)\n\n    if es_ruta_publica(request.url.path):\n        return await call_next(request)\n\n    auth_header = request.headers.get(\"Authorization\")\n    if not auth_header or not auth_header.startswith(\"Bearer \"):\n        return JSONResponse(\n            status_code=status.HTTP_401_UNAUTHORIZED,\n            content={\"detail\": \"Se requiere token de autenticaci\u00f3n\"},\n            headers={\n                **_cors_headers(request),\n                \"WWW-Authenticate\": \"Bearer\",\n            },\n        )\n\n    token = auth_header.split(\" \")[1]\n    payload = verificar_token(token)\n\n    if payload is None:\n        return JSONResponse(\n            status_code=status.HTTP_401_UNAUTHORIZED,\n            content={\"detail\": \"Token inv\u00e1lido o expirado\"},\n            headers={\n                **_cors_headers(request),\n                \"WWW-Authenticate\": \"Bearer\",\n            },\n        )\n\n    # BUG-006 FIX: el login emite 'role' (ingl\u00e9s), no 'rol' (espa\u00f1ol)\n    request.state.usuario_id  = payload.get(\"sub\")\n    request.state.usuario_rol = payload.get(\"role\", \"\")\n    request.state.token       = token\n\n    return await call_next(request)"

target.write_text(NEW_CONTENT, encoding="utf-8")
print("✅ Backend/api_gateway/app/middleware/auth.py — parcheado correctamente")
print()
print("Cambios aplicados:")
print("  BUG-006  payload.get(\'rol\') → payload.get(\'role\')")
print("  BUG-012  CORS_HEADERS (variable estática con *) → _cors_headers(request)")
print("           en ambos JSONResponse de error 401")
