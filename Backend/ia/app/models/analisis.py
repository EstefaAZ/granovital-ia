# ==============================================================
# modulo_04_ia / app/models/analisis.py
# ORM SQLAlchemy - tablas de resultados de IA
#
#   tbl_analisis_imagen     RF-05 enfermedades | RF-06 plagas
#   tbl_prediccion_fito     RF-07 prediccion fitosanitaria
#   tbl_recomendacion_riego RF-08 riego
#   tbl_recomendacion_fert  RF-09 fertilizacion
#
# Cada tabla guarda el resultado completo incluyendo:
#   - entrada usada (imagen codificada / datos de sensores)
#   - salida del modelo (diagnostico, confianza, recomendacion)
#   - metadatos del modelo (version, timestamp)
# Esto permite auditar y comparar versiones (RNF-08)
# ==============================================================

from datetime import datetime, timezone  # C-01 FIX
from sqlalchemy import (
    Enum, ForeignKey, Text,
)
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class AnalisisImagen(Base):
    """
    tbl_analisis_imagen
    Almacena cada analisis de imagen realizado por el modelo CNN.

    RF-05: tipo_analisis='enfermedad'
           Analiza hoja de cafe para detectar Roya, Mancha de Hierro,
           CBD (broca del cafe), Antracnosis y estado Sano.

    RF-06: tipo_analisis='plaga'
           Identifica la Broca del Cafe (Hypothenemus hampei),
           Minador de la Hoja, Trips y Acaro Rojo.

    El flujo sigue el Diagrama de Secuencia oficial del proyecto:
      1 seleccionarImagen -> 2 cargarImagen -> 3 enviarImagen ->
      4 procesarImagen -> 5 enviarAIA -> 6 analizarImagen ->
      7 generarDiagnostico -> 8 retornarResultado ->
      9 guardarResultado -> 10 mostrarResultados
    """
    __tablename__ = "tbl_analisis_imagen"

    id_analisis: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tipo_analisis: Mapped[str] = mapped_column(
        Enum("enfermedad", "plaga"),
        nullable=False,
        comment="RF-05 enfermedad | RF-06 plaga",
    )
    diagnostico: Mapped[str] = mapped_column(
        nullable=False,
        comment="Clase predicha por el modelo (ej: Roya, Broca, Sano)",
    )
    confianza: Mapped[float] = mapped_column(
        nullable=False,
        comment="Probabilidad de la clase predicha (0.0 - 1.0)",
    )
    # Top-3 de clases con sus probabilidades en formato JSON
    top_clases: Mapped[str] = mapped_column(
        Text, nullable=True,
        comment='JSON: [{"clase":"Roya","prob":0.92}, ...]',
    )
    recomendacion: Mapped[str] = mapped_column(
        Text, nullable=False,
        comment="Recomendacion tecnica generada segun el diagnostico",
    )
    nivel_urgencia: Mapped[str] = mapped_column(
        Enum("bajo", "medio", "alto", "critico"),
        nullable=False,
        default="medio",
    )
    # Metadata del modelo para trazabilidad RNF-08
    version_modelo: Mapped[str] = mapped_column(nullable=True)
    tiempo_inferencia: Mapped[float] = mapped_column(
        nullable=True,
        comment="Tiempo de inferencia en segundos - control RNF-01",
    )
    # Nombre del archivo original subido por el usuario
    nombre_imagen: Mapped[str] = mapped_column(nullable=True)
    tamano_imagen_kb: Mapped[int] = mapped_column(nullable=True)
    fecha_analisis: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)
    # BUG-004 FIX: ForeignKey real en SQLAlchemy (antes era solo un comentario)
    id_cultivo: Mapped[int] = mapped_column(
        ForeignKey("tbl_cultivo.id_cultivo", ondelete="RESTRICT", use_alter=True),
        nullable=False,
        comment="FK a tbl_cultivo con integridad referencial real",
    )
    id_usuario: Mapped[int] = mapped_column(nullable=False)

    def __repr__(self):
        return (
            f"<AnalisisImagen id={self.id_analisis} "
            f"tipo={self.tipo_analisis} dx='{self.diagnostico}' "
            f"conf={self.confianza:.2f}>"
        )


class PrediccionFitosanitaria(Base):
    """
    tbl_prediccion_fito
    RF-07: prediccion de riesgo fitosanitario basada en
    datos ambientales del cultivo (temperatura, humedad, precipitacion).

    RN-03: el servicio verifica que los datos del M03 sean
    validos (< 24h) antes de ejecutar la prediccion.

    El modelo usa un clasificador de riesgo con 4 niveles.
    """
    __tablename__ = "tbl_prediccion_fito"

    id_prediccion: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    nivel_riesgo: Mapped[str] = mapped_column(
        Enum("bajo", "moderado", "alto", "critico"),
        nullable=False,
    )
    probabilidad_riesgo: Mapped[float] = mapped_column(nullable=False)
    # Factores de riesgo detectados
    factores_riesgo: Mapped[str] = mapped_column(
        Text, nullable=True,
        comment='JSON: ["humedad_alta", "temperatura_optima_roya"]',
    )
    enfermedades_prob: Mapped[str] = mapped_column(
        Text, nullable=True,
        comment='JSON: {"Roya": 0.78, "Mancha_Hierro": 0.45}',
    )
    recomendacion: Mapped[str] = mapped_column(Text, nullable=False)
    # Snapshot de datos usados (para auditoria RNF-08)
    temperatura_usada: Mapped[float] = mapped_column(nullable=True)
    humedad_usada: Mapped[float] = mapped_column(nullable=True)
    precipitacion_usada: Mapped[float] = mapped_column(nullable=True)
    version_modelo: Mapped[str] = mapped_column(nullable=True)
    fecha_prediccion: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)
    # BUG-004 FIX: ForeignKey real en SQLAlchemy (antes era solo un comentario)
    id_cultivo: Mapped[int] = mapped_column(
        ForeignKey("tbl_cultivo.id_cultivo", ondelete="RESTRICT", use_alter=True),
        nullable=False,
        comment="FK a tbl_cultivo con integridad referencial real",
    )
    id_usuario: Mapped[int] = mapped_column(nullable=False)


class RecomendacionRiego(Base):
    """
    tbl_recomendacion_riego
    RF-08: recomendacion automatica de riego basada en
    humedad del suelo, temperatura y precipitacion.

    RN-03: requiere datos validos de ambos sensores.
    """
    __tablename__ = "tbl_recomendacion_riego"

    id_reco: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    necesita_riego: Mapped[str] = mapped_column(
        Enum("si", "no", "condicional"),
        nullable=False,
    )
    cantidad_litros_m2: Mapped[float] = mapped_column(
        nullable=True,
        comment="Litros por metro cuadrado recomendados",
    )
    frecuencia_dias: Mapped[int] = mapped_column(nullable=True)
    momento_optimo: Mapped[str] = mapped_column(
        Enum("manana", "tarde", "noche", "cualquiera"),
        nullable=True,
    )
    justificacion: Mapped[str] = mapped_column(Text, nullable=False)
    recomendacion: Mapped[str] = mapped_column(Text, nullable=False)
    nivel_urgencia: Mapped[str] = mapped_column(
        Enum("bajo", "medio", "alto"), nullable=False, default="medio"
    )
    # Snapshot datos entrada
    humedad_suelo_usada: Mapped[float] = mapped_column(nullable=True)
    temperatura_usada: Mapped[float] = mapped_column(nullable=True)
    precipitacion_usada: Mapped[float] = mapped_column(nullable=True)
    version_modelo: Mapped[str] = mapped_column(nullable=True)
    fecha_recomendacion: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)
    # BUG-004 FIX: ForeignKey real en SQLAlchemy (antes era solo un comentario)
    id_cultivo: Mapped[int] = mapped_column(
        ForeignKey("tbl_cultivo.id_cultivo", ondelete="RESTRICT", use_alter=True),
        nullable=False,
        comment="FK a tbl_cultivo con integridad referencial real",
    )
    id_usuario: Mapped[int] = mapped_column(nullable=False)


class RecomendacionFertilizacion(Base):
    """
    tbl_recomendacion_fert
    RF-09: recomendacion de tipo y cantidad de fertilizante
    segun el estado del suelo (NPK, pH, materia organica).

    RN-03: requiere datos de suelo actualizados.
    """
    __tablename__ = "tbl_recomendacion_fert"

    id_reco_fert: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tipo_fertilizante: Mapped[str] = mapped_column(
        nullable=False,
        comment="Ej: Urea, DAP, KCl, Fertilizante completo 17-6-18-2",
    )
    dosis_kg_ha: Mapped[float] = mapped_column(
        nullable=True,
        comment="Dosis recomendada en kg por hectarea",
    )
    frecuencia_aplicacion: Mapped[str] = mapped_column(nullable=True)
    metodo_aplicacion: Mapped[str] = mapped_column(
        Enum("foliar", "edafico", "fertiriego", "cualquiera"),
        nullable=True,
    )
    nutrientes_deficientes: Mapped[str] = mapped_column(
        Text, nullable=True,
        comment='JSON: ["N", "P"] - nutrientes por debajo del minimo',
    )
    justificacion: Mapped[str] = mapped_column(Text, nullable=False)
    recomendacion: Mapped[str] = mapped_column(Text, nullable=False)
    nivel_urgencia: Mapped[str] = mapped_column(
        Enum("bajo", "medio", "alto"), nullable=False, default="medio"
    )
    # Snapshot datos entrada
    ph_suelo_usado: Mapped[float] = mapped_column(nullable=True)
    nitrogeno_usado: Mapped[float] = mapped_column(nullable=True)
    fosforo_usado: Mapped[float] = mapped_column(nullable=True)
    potasio_usado: Mapped[float] = mapped_column(nullable=True)
    materia_organica_usada: Mapped[float] = mapped_column(nullable=True)
    version_modelo: Mapped[str] = mapped_column(nullable=True)
    fecha_recomendacion: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)
    # BUG-004 FIX: ForeignKey real en SQLAlchemy (antes era solo un comentario)
    id_cultivo: Mapped[int] = mapped_column(
        ForeignKey("tbl_cultivo.id_cultivo", ondelete="RESTRICT", use_alter=True),
        nullable=False,
        comment="FK a tbl_cultivo con integridad referencial real",
    )
    id_usuario: Mapped[int] = mapped_column(nullable=False)
