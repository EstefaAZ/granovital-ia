# =============================================================
# Dockerfile — GranoVital IA FastAPI
# Imagen ligera Python 3.11 slim
# =============================================================

FROM python:3.11-slim

# Metadatos
LABEL maintainer="GranoVital IA Team"
LABEL description="API REST GranoVital IA — Gestión inteligente del café"

# Variables de entorno para Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Directorio de trabajo
WORKDIR /app

# Dependencias del sistema (mínimas)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Instalar dependencias Python primero (aprovecha caché de Docker)
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copiar el código fuente
COPY . .

# Puerto expuesto
EXPOSE 8006

# Usuario no-root por seguridad (RNF-04)
RUN adduser --disabled-password --gecos "" appuser
USER appuser

# Comando de inicio
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8006", "--workers", "2"]
