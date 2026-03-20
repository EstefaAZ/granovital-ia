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

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, DateTime, Numeric,
    Enum, ForeignKey, Text, LargeBinary, Float,
)
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

    id_analisis        = Column(Integer, primary_key=True, autoincrement=True)
    tipo_analisis      = Column(
        Enum("enfermedad", "plaga"),
        nullable=False,
        comment="RF-05 enfermedad | RF-06 plaga",
    )
    diagnostico        = Column(
        String(120), nullable=False,
        comment="Clase predicha por el modelo (ej: Roya, Broca, Sano)",
    )
    confianza          = Column(
        Float, nullable=False,
        comment="Probabilidad de la clase predicha (0.0 - 1.0)",
    )
    # Top-3 de clases con sus probabilidades en formato JSON
    top_clases         = Column(
        Text, nullable=True,
        comment='JSON: [{"clase":"Roya","prob":0.92}, ...]',
    )
    recomendacion      = Column(
        Text, nullable=False,
        comment="Recomendacion tecnica generada segun el diagnostico",
    )
    nivel_urgencia     = Column(
        Enum("bajo", "medio", "alto", "critico"),
        nullable=False,
        default="medio",
    )
    # Metadata del modelo para trazabilidad RNF-08
    version_modelo     = Column(String(30), nullable=True)
    tiempo_inferencia  = Column(
        Float, nullable=True,
        comment="Tiempo de inferencia en segundos - control RNF-01",
    )
    # Nombre del archivo original subido por el usuario
    nombre_imagen      = Column(String(200), nullable=True)
    tamano_imagen_kb   = Column(Integer, nullable=True)
    fecha_analisis     = Column(DateTime, nullable=False, default=datetime.utcnow)
    id_cultivo = Column(
    Integer,
    nullable=False,
    comment="FK a tbl_cultivo - integridad gestionada por MySQL",
    )
    id_usuario         = Column(Integer, nullable=False)

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

    id_prediccion      = Column(Integer, primary_key=True, autoincrement=True)
    nivel_riesgo       = Column(
        Enum("bajo", "moderado", "alto", "critico"),
        nullable=False,
    )
    probabilidad_riesgo = Column(Float, nullable=False)
    # Factores de riesgo detectados
    factores_riesgo    = Column(
        Text, nullable=True,
        comment='JSON: ["humedad_alta", "temperatura_optima_roya"]',
    )
    enfermedades_prob  = Column(
        Text, nullable=True,
        comment='JSON: {"Roya": 0.78, "Mancha_Hierro": 0.45}',
    )
    recomendacion      = Column(Text, nullable=False)
    # Snapshot de datos usados (para auditoria RNF-08)
    temperatura_usada  = Column(Float, nullable=True)
    humedad_usada      = Column(Float, nullable=True)
    precipitacion_usada = Column(Float, nullable=True)
    version_modelo     = Column(String(30), nullable=True)
    fecha_prediccion   = Column(DateTime, nullable=False, default=datetime.utcnow)
    id_cultivo = Column(
    Integer,
    nullable=False,
    comment="FK a tbl_cultivo - integridad gestionada por MySQL",
    )
    id_usuario         = Column(Integer, nullable=False)


class RecomendacionRiego(Base):
    """
    tbl_recomendacion_riego
    RF-08: recomendacion automatica de riego basada en
    humedad del suelo, temperatura y precipitacion.

    RN-03: requiere datos validos de ambos sensores.
    """
    __tablename__ = "tbl_recomendacion_riego"

    id_reco            = Column(Integer, primary_key=True, autoincrement=True)
    necesita_riego     = Column(
        Enum("si", "no", "condicional"),
        nullable=False,
    )
    cantidad_litros_m2 = Column(
        Numeric(8, 2), nullable=True,
        comment="Litros por metro cuadrado recomendados",
    )
    frecuencia_dias    = Column(Integer, nullable=True)
    momento_optimo     = Column(
        Enum("manana", "tarde", "noche", "cualquiera"),
        nullable=True,
    )
    justificacion      = Column(Text, nullable=False)
    recomendacion      = Column(Text, nullable=False)
    nivel_urgencia     = Column(
        Enum("bajo", "medio", "alto"), nullable=False, default="medio"
    )
    # Snapshot datos entrada
    humedad_suelo_usada = Column(Float, nullable=True)
    temperatura_usada   = Column(Float, nullable=True)
    precipitacion_usada = Column(Float, nullable=True)
    version_modelo      = Column(String(30), nullable=True)
    fecha_recomendacion = Column(DateTime, nullable=False, default=datetime.utcnow)
    id_cultivo = Column(
    Integer,
    nullable=False,
    comment="FK a tbl_cultivo - integridad gestionada por MySQL",
    )
    id_usuario          = Column(Integer, nullable=False)


class RecomendacionFertilizacion(Base):
    """
    tbl_recomendacion_fert
    RF-09: recomendacion de tipo y cantidad de fertilizante
    segun el estado del suelo (NPK, pH, materia organica).

    RN-03: requiere datos de suelo actualizados.
    """
    __tablename__ = "tbl_recomendacion_fert"

    id_reco_fert       = Column(Integer, primary_key=True, autoincrement=True)
    tipo_fertilizante  = Column(
        String(120), nullable=False,
        comment="Ej: Urea, DAP, KCl, Fertilizante completo 17-6-18-2",
    )
    dosis_kg_ha        = Column(
        Numeric(8, 2), nullable=True,
        comment="Dosis recomendada en kg por hectarea",
    )
    frecuencia_aplicacion = Column(String(80), nullable=True)
    metodo_aplicacion  = Column(
        Enum("foliar", "edafico", "fertiriego", "cualquiera"),
        nullable=True,
    )
    nutrientes_deficientes = Column(
        Text, nullable=True,
        comment='JSON: ["N", "P"] - nutrientes por debajo del minimo',
    )
    justificacion      = Column(Text, nullable=False)
    recomendacion      = Column(Text, nullable=False)
    nivel_urgencia     = Column(
        Enum("bajo", "medio", "alto"), nullable=False, default="medio"
    )
    # Snapshot datos entrada
    ph_suelo_usado      = Column(Float, nullable=True)
    nitrogeno_usado     = Column(Float, nullable=True)
    fosforo_usado       = Column(Float, nullable=True)
    potasio_usado       = Column(Float, nullable=True)
    materia_organica_usada = Column(Float, nullable=True)
    version_modelo      = Column(String(30), nullable=True)
    fecha_recomendacion = Column(DateTime, nullable=False, default=datetime.utcnow)
    id_cultivo = Column(
    Integer,
    nullable=False,
    comment="FK a tbl_cultivo - integridad gestionada por MySQL",
    )
    id_usuario          = Column(Integer, nullable=False)
