# Script de arranque local para backend granovital_login
# Define variables seguras para desarrollo local y ejecuta Uvicorn

$env:APP_NAME = "GranoVital IA Local"
$env:DEBUG = "True"
$env:DB_HOST = "localhost"
$env:DB_PORT = "3306"
$env:DB_NAME = "granovital_ia"
$env:DB_USER = "root"
$env:DB_PASSWORD = ""
$env:JWT_SECRET_KEY = "cambia-esta-clave-en-produccion"
$env:JWT_ALGORITHM = "HS256"
$env:JWT_ACCESS_TOKEN_EXPIRE_MINUTES = "60"
$env:JWT_REFRESH_TOKEN_EXPIRE_DAYS = "7"
$env:REDIS_HOST = "localhost"
$env:REDIS_PORT = "6379"
$env:REDIS_DB = "0"
$env:REDIS_PASSWORD = ""

Write-Host "Iniciando servicio en http://localhost:8010 ..."
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8010
