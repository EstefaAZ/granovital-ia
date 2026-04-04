# ==============================================================
# modulo_06_mercado / app/models/mercado.py
# ORM SQLAlchemy — Tablas del Módulo de Mercado
#
# tbl_precio_mercado    RF-13  histórico de precios de referencia
# tbl_analisis_precio   RF-13  análisis y proyecciones de precio
# tbl_analisis_demanda  RF-14  análisis de demanda y oportunidades
#
# DECISIÓN DE DISEÑO:
# El módulo opera sobre dos fuentes de datos complementarias:
#
# 1. Datos INTERNOS del sistema:
#    - Precios de venta reales registrados en tbl_trazabilidad_lote
#      (módulo 05, campo precio_venta_kg).
#    - Volúmenes vendidos por categoría y período.
#    Estos son los datos más confiables porque son transaccionales.
#
# 2. Datos de REFERENCIA de mercado:
#    - Registros manuales del Comercializador con precios FNC,
#      NY Stock Exchange (contrato C) y precios locales.
#    - Permiten contextualizar los precios propios versus el mercado.
#
# NOTA ARQUITECTÓNICA sobre RF-13 y RF-14:
# Los requisitos son de prioridad "Baja" en el documento y no
# especifican la fuente de datos externa. La implementación
# utiliza datos del propio sistema (lotes vendidos del M05)
# como fuente primaria de análisis, complementada con registros
# manuales de referencia para el contexto de mercado.
# Esta decisión está alineada con la estrategia de operación
# en zonas rurales con conectividad limitada (RNF-10).
# ==============================================================

from datetime import datetime, timezone
from sqlalchemy import (
    DateTime, Enum, Float, ForeignKey,
    Integer, Numeric, String, Text, Boolean,
)
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


FUENTES_PRECIO = ("fnc", "bolsa_ny", "mercado_local", "manual", "propio_sistema")
TIPOS_CAFE     = ("pergamino_seco", "verde_exportacion", "tostado", "especial")
TENDENCIAS     = ("alza", "baja", "estable", "volatil")


class PrecioMercado(Base):
    """
    tbl_precio_mercado
    RF-13: registro histórico de precios de referencia del café.

    Almacena tanto los precios del propio sistema (obtenidos de
    tbl_trazabilidad_lote.precio_venta_kg) como precios externos
    ingresados manualmente por el Comercializador para comparación.

    Fuentes:
      fnc           Precio base FNC (Federación Nacional de Cafeteros)
      bolsa_ny      Contrato C - New York Coffee Exchange (ICE)
      mercado_local Precio pagado en la plaza o cooperativa local
      manual        Precio de referencia ingresado manualmente
      propio_sistema Precio real obtenido de una venta propia registrada
    """
    __tablename__ = "tbl_precio_mercado"

    id_precio: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    fuente: Mapped[str] = mapped_column(Enum(*FUENTES_PRECIO), nullable=False)
    tipo_cafe: Mapped[str] = mapped_column(
        Enum(*TIPOS_CAFE),
        nullable=False,
        default="pergamino_seco",
    )
    precio_cop_kg: Mapped[float] = mapped_column(
        Numeric(12, 2), nullable=False,
        comment="Precio en COP por kilogramo",
    )
    precio_usd_lb: Mapped[float] = mapped_column(
        Numeric(8, 4), nullable=True,
        comment="Precio en USD por libra (opcional, para referencia bolsa NY)",
    )
    variedad: Mapped[str] = mapped_column(
        Enum("castillo", "colombia", "caturra", "cenicafe_1", "mezcla", "otro"),
        nullable=True,
    )
    categoria_calidad: Mapped[str] = mapped_column(
        Enum("supremo", "excelso_extra", "excelso", "corriente", "pasilla", "todas"),
        nullable=False,
        default="todas",
    )
    region: Mapped[str] = mapped_column(String(80), nullable=True)
    notas: Mapped[str] = mapped_column(Text, nullable=True)
    # Si el precio viene de una venta propia del M05
    id_lote_origen: Mapped[int] = mapped_column(Integer, nullable=True)
    id_usuario: Mapped[int] = mapped_column(Integer, nullable=False)
    fecha_precio: Mapped[datetime] = mapped_column(
        DateTime, nullable=False,
        comment="Fecha a la que corresponde el precio (no la fecha de ingreso)",
    )
    fecha_registro: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return (
            f"<Precio {self.fuente} ${self.precio_cop_kg}/kg "
            f"{self.fecha_precio.strftime('%Y-%m')}>"
        )


class AnalisisPrecio(Base):
    """
    tbl_analisis_precio
    RF-13: resultado de un análisis de precios generado para el Comercializador.

    Incluye métricas estadísticas calculadas sobre el histórico:
      precio_promedio   Media del período analizado
      precio_minimo     Mínimo en el período
      precio_maximo     Máximo en el período
      variacion_pct     Variación porcentual vs período anterior
      tendencia         Clasificación: alza / baja / estable / volátil
      precio_proyectado Estimación para el próximo período (promedio móvil)

    La proyección usa promedio móvil ponderado (WMA) de 3 períodos,
    que es el método más adecuado para series cortas sin entrenamiento
    de modelos ML, coherente con el enfoque del proyecto.
    """
    __tablename__ = "tbl_analisis_precio"

    id_analisis: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    periodo_inicio: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    periodo_fin: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    tipo_cafe: Mapped[str] = mapped_column(Enum(*TIPOS_CAFE), nullable=False, default="pergamino_seco")
    fuente_analizada: Mapped[str] = mapped_column(String(60), nullable=False, default="todas")
    precio_promedio: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    precio_minimo: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    precio_maximo: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    variacion_pct: Mapped[float] = mapped_column(
        Float, nullable=True,
        comment="% de variacion respecto al periodo anterior equivalente",
    )
    tendencia: Mapped[str] = mapped_column(Enum(*TENDENCIAS), nullable=False, default="estable")
    precio_proyectado: Mapped[float] = mapped_column(
        Numeric(12, 2), nullable=True,
        comment="Proyeccion WMA-3 para el siguiente mes",
    )
    alerta_activa: Mapped[bool] = mapped_column(Boolean, default=False)
    mensaje_alerta: Mapped[str] = mapped_column(String(300), nullable=True)
    recomendacion: Mapped[str] = mapped_column(Text, nullable=False)
    num_registros_base: Mapped[int] = mapped_column(
        Integer, nullable=False,
        comment="Cantidad de precios usados para calcular el analisis",
    )
    version_metodologia: Mapped[str] = mapped_column(String(30), default="wma-3-periodos-1.0")
    id_usuario: Mapped[int] = mapped_column(Integer, nullable=False)
    fecha_analisis: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return (
            f"<AnalisisPrecio tendencia={self.tendencia} "
            f"prom=${self.precio_promedio} alerta={self.alerta_activa}>"
        )


class AnalisisDemanda(Base):
    """
    tbl_analisis_demanda
    RF-14: análisis de la demanda del mercado del café.

    La demanda se infiere a partir de los datos internos del sistema:
      - Volumen de lotes vendidos en el período (M05)
      - Velocidad de venta: tiempo promedio entre aprobación y venta
      - Categorías más demandadas
      - Compradores recurrentes
      - Destinos de exportación frecuentes

    Además el Comercializador puede registrar observaciones de demanda
    externos (ferias, pedidos anticipados, tendencias de consumo).
    """
    __tablename__ = "tbl_analisis_demanda"

    id_demanda: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    periodo_inicio: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    periodo_fin: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    # Métricas calculadas del M05
    total_lotes_vendidos: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    kg_totales_vendidos: Mapped[float] = mapped_column(
        Numeric(14, 2), nullable=False, default=0,
        comment="Kilogramos de pergamino seco vendidos en el periodo",
    )
    kg_promedio_por_lote: Mapped[float] = mapped_column(Numeric(10, 2), nullable=True)
    dias_promedio_venta: Mapped[float] = mapped_column(
        Float, nullable=True,
        comment="Dias promedio entre aprobacion del lote y registro de venta",
    )
    categoria_mas_demandada: Mapped[str] = mapped_column(String(40), nullable=True)
    comprador_frecuente: Mapped[str] = mapped_column(String(120), nullable=True)
    destino_principal: Mapped[str] = mapped_column(String(80), nullable=True)
    # Clasificación de la demanda
    nivel_demanda: Mapped[str] = mapped_column(
        Enum("baja", "media", "alta", "muy_alta"),
        nullable=False,
        default="media",
    )
    variacion_demanda_pct: Mapped[float] = mapped_column(
        Float, nullable=True,
        comment="% de variacion vs periodo anterior",
    )
    # Observaciones del Comercializador (contexto externo)
    observaciones_mercado: Mapped[str] = mapped_column(Text, nullable=True)
    oportunidades: Mapped[str] = mapped_column(
        Text, nullable=True,
        comment="Oportunidades comerciales identificadas en el periodo",
    )
    riesgos: Mapped[str] = mapped_column(
        Text, nullable=True,
        comment="Riesgos de demanda identificados",
    )
    recomendacion: Mapped[str] = mapped_column(Text, nullable=False)
    id_usuario: Mapped[int] = mapped_column(Integer, nullable=False)
    fecha_analisis: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return (
            f"<AnalisisDemanda nivel={self.nivel_demanda} "
            f"lotes={self.total_lotes_vendidos} "
            f"kg={self.kg_totales_vendidos}>"
        )
