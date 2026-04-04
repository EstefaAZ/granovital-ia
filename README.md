# Granovital IA

## Architecture Overview
Granovital IA es una solución modular basada en microservicios para la gestión de cultivo, monitoreo ambiental, trazabilidad y comercio. Cada servicio backend está implementado en Python/FastAPI y se comunica por REST.

## Project Structure
```
granovital-ia/
│
├── frontend/             # Frontend Vite + React
├── backend/              # Backend microservicios FastAPI (Python)
│   ├── api_gateway/
│   ├── cultivos/
│   ├── ia/
│   ├── mercado/
│   ├── monitoreo/
│   ├── reportes/
│   └── trazabilidad/
└── README.md             # Documentación general
```

## Technology Stack
- Frontend: React.js + Vite
- Backend: Python 3.11+, FastAPI, SQLAlchemy, Pydantic
- Base de datos: MySQL (o MariaDB) + SQLAlchemy ORM
- Almacenamiento de sesiones/tokens: Redis (opcional)
- Implementación / DevOps: Docker, docker-compose

## Setup Instructions
1. **Clonar el repositorio**
   ```bash
   git clone https://github.com/EstefaAZ/granovital-ia.git
   cd granovital-ia
   ```

2. **Instalar dependencias**
   - Frontend:
     ```bash
     cd frontend
     npm install
     ```
   - Cada servicio backend (ejemplo `granovital_login`):
     ```bash
     cd backend/granovital_login/granovital
     python -m pip install -r requirements.txt
     ```

3. **Configurar variables de entorno**
   - Copiar `backend/granovital_login/granovital/.env.example` a `backend/granovital_login/granovital/.env`.
   - Los valores por defecto permiten arranque local mínimo (DB local, clave JWT de prueba).
   - Asegúrate de ajustar `JWT_SECRET_KEY` en producción.

4. **Iniciar MySQL y Redis localmente** (opcional, no obligatorio para pruebas unitarias)
   - MySQL: `mysql` o `docker run --name granovital-db ...`
   - Redis: `redis-server` o `docker run --name granovital-redis ...`

## Ejecución local
- Frontend
  ```bash
  cd frontend
  npm run dev
  ```

- Backend (cada servicio)
  ```bash
  cd backend/granovital_login/granovital
  uvicorn app.main:app --reload --host 0.0.0.0 --port 8010
  ```

- Usar script de arranque local (Windows PowerShell)
  ```powershell
  cd backend/granovital_login/granovital
  .\start_local.ps1
  ```

- Con Docker Compose
  ```bash
  docker-compose up --build
  ```

## Monitoreo y observabilidad (producción)
- Logging estructurado con `logging` en cada servicio.
- Integración recomendada con Sentry (`SENTRY_DSN`) para errores de backend.
- Azure Application Insights para trazabilidad de endpoints y métricas de request/response.
- Alertas: tiempo de respuesta > 2s, tasa de 5xx > 1%, % de token inválidos.

## QA y pruebas
- Ejecutar los tests con:
  ```bash
  pytest -q
  ```
- Cobertura:
  ```bash
  pytest --cov=backend --cov-report=html
  ```

## Casos Gherkin: flujo registro -> IA -> reporte
```gherkin
Feature: Flujo completo de cultivo, análisis IA y reporte
  As a caficultor
  I want to register a crop, run IA analysis, and get a report
  So that I can monitor status and trazabilidad

  Background:
    Given el servicio está disponible en /health
    And existe un usuario autenticado con rol Caficultor

  Scenario: Registro de cultivo con datos válidos
    When el usuario envía POST /cultivos con:
      | nombre_cultivo | Finca La Esperanza |
      | ubicacion      | Andes, Antioquia   |
      | area_hectareas | 3.5                |
      | variedad_cafe  | Castillo           |
    Then la respuesta es 201
    And el payload contiene id_cultivo y estado 'creado'

  Scenario: Ejecutar análisis IA para cultivo registrado
    Given un cultivo creado con id_cultivo = 1
    When el usuario envía POST /ia/analisis con:
      | id_cultivo | 1 |
      | tipo       | prediccion_enfermedades |
    Then la respuesta es 200
    And el payload contiene campo 'resultado' y 'confianza'

  Scenario: Generar reporte basado en análisis IA
    Given un análisis IA completado para id_cultivo = 1
    When el usuario solicita GET /reportes?cultivo_id=1
    Then la respuesta es 200
    And el reporte incluye resumen del análisis y recomendaciones
```

## Instrucciones para pipeline CI/CD (GitHub Actions)
1. Archivo: `.github/workflows/test-and-deploy.yml`
2. Pasos clave:
   - checkout
   - setup-python 3.11
   - install-dependencies (cada servicio):
     `pip install -r backend/<servicio>/requirements.txt`
   - set `PYTHONPATH` por servicio:
     `PYTHONPATH=backend/<servicio>/<subcarpeta> pytest -q`
   - ejecutar lint:
     `ruff check backend frontend`
   - ejecutar pruebas con cobertura:
     `pytest --cov=backend --cov-report=xml`
   - publicar resultados `codecov` opcional
   - build Docker images:
     `docker build -t granovital-<servicio> backend/<servicio>`
   - push a registro (ACR/ECR):
     `docker push <REGISTRY>/granovital-<servicio>`
   - despliegue (az cli):
     `az webapp up --name <APP> --resource-group <RG> --plan <PLAN> --src-path backend/<servicio>`

3. Ejemplo rápido:
```yaml
name: CI/CD
on:
  pull_request:
  push:
    branches: [main]

jobs:
  tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: |
          python -m pip install --upgrade pip
          cd backend/granovital_login/granovital
          pip install -r requirements.txt
          PYTHONPATH=$(pwd) pytest -q
          cd ../../cultivos
          pip install -r requirements.txt
          PYTHONPATH=$(pwd) pytest -q
      - run: |
          cd backend/ia/app
          pip install -r requirements.txt
          PYTHONPATH=$(pwd) pytest -q
      - run: |
          cd backend/mercado
          pip install -r requirements.txt
          PYTHONPATH=$(pwd) pytest -q
      - run: |
          cd backend/monitoreo
          pip install -r requirements.txt
          PYTHONPATH=$(pwd) pytest -q
      - run: |
          cd backend/reportes
          pip install -r requirements.txt
          PYTHONPATH=$(pwd) pytest -q
      - run: |
          cd backend/trazabilidad
          pip install -r requirements.txt
          PYTHONPATH=$(pwd) pytest -q

  deploy:
    needs: tests
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v4
      - uses: azure/login@v1
        with:
          creds: ${{ secrets.AZURE_CREDENTIALS }}
      - run: |
          az account set --subscription ${{ secrets.AZURE_SUBSCRIPTION_ID }}
          az webapp up --name my-granovital-api --resource-group my-rg --runtime "PYTHON:3.11" --src-path backend/api_gateway
```


