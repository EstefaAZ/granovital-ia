# ==============================================================
# modulo_05_trazabilidad / app/models/trazabilidad.py
# ORM SQLAlchemy — Tablas del Modulo de Trazabilidad
#
# tbl_trazabilidad_lote    RF-10  cadena completa del lote
# tbl_evento_trazabilidad  RF-10  log inmutable de eventos
# tbl_control_secado       RF-11  lecturas de temperatura/tiempo
# tbl_clasificacion_grano  RF-12  resultado de clasificacion IA
#
# DIAGRAMA DE ESTADOS DEL LOTE (implementado via campo 'estado'):
#   registrarLote    -> Registrado
#   confirmarRegistro -> Disponible
#   enviarAAnalisis  -> En Analisis (RF-12)
#   resultadoIA(aprobado) -> Aprobado
#   resultadoIA(defecto)  -> Con Problema
#   ventaRealizada   -> Vendido
#   eliminarLote     -> Eliminado (solo desde Registrado o Disponible)
#
# RN-04 INMUTABILIDAD: una vez el lote pasa a estado 'aprobado'
# o 'vendido', su registro de trazabilidad no puede ser
# modificado por el Productor. Solo el Administrador puede
# hacer correcciones, que quedan registradas en
# tbl_evento_trazabilidad con motivo y usuario que lo hizo.
# ==============================================================

import hashlib
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import (
    Column, DateTime, Enum, Float, ForeignKey,
    Integer, Numeric, String, Text, Boolean,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


# Estados del lote — Diagrama de Estados oficial del proyecto
ESTADOS_LOTE = (
    "registrado",
    "disponible",
    "en_analisis",
    "aprobado",
    "con_problema",
    "vendido",
    "eliminado",
)


class TrazabilidadLote(Base):
    """
    tbl_trazabilidad_lote
    Registro maestro de trazabilidad de un lote de cafe.

    RF-10: almacena la cadena completa desde el cultivo de origen
    hasta la venta, cumpliendo RN-02 (trazabilidad obligatoria
    antes de comercializar).

    RN-04: el campo 'hash_integridad' se calcula al validar el
    lote (transicion a 'aprobado'). Cualquier modificacion
    posterior al hash invalida la integridad del registro,
    permitiendo detectar alteraciones (RNF-05).

    RN-05: el campo 'codigo_qr' es la URL publica que el
    consumidor puede escanear para ver solo los campos
    autorizados (sin datos internos del sistema).
    """
    __tablename__ = "tbl_trazabilidad_lote"

    id_lote: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    codigo_lote: Mapped[str] = mapped_column(
        String(40), nullable=False, unique=True,
        comment="Codigo unico legible, ej: GV-2025-0042",
    )

    # --- Datos de origen ---
    variedad_cafe: Mapped[str] = mapped_column(
        Enum("castillo", "colombia", "caturra", "cenicafe_1", "otro"),
        nullable=False,
    )
    fecha_cosecha: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    metodo_cosecha: Mapped[str] = mapped_column(
        Enum("manual_selectiva", "manual_global", "mecanica"),
        nullable=False,
        default="manual_selectiva",
    )
    kg_cereza_cosechados: Mapped[float] = mapped_column(
        Numeric(10, 2), nullable=False,
        comment="Kilogramos de cafe cereza cosechados",
    )

    # --- Proceso ---
    metodo_beneficio: Mapped[Optional[str]] = mapped_column(
        Enum("lavado", "natural", "honey", "anaerobic"),
        nullable=True,
        comment="Metodo de beneficio post-cosecha",
    )
    fecha_inicio_secado: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    fecha_fin_secado: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    kg_pergamino_seco: Mapped[Optional[float]] = mapped_column(
        Numeric(10, 2), nullable=True,
        comment="Kg de cafe pergamino seco obtenidos",
    )

    # --- Calidad ---
    humedad_final_pct: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True,
        comment="% de humedad del grano al finalizar secado",
    )
    clasificacion_calidad: Mapped[str] = mapped_column(
        Enum("supremo", "excelso_extra", "excelso", "corriente", "pasilla", "sin_clasificar"),
        nullable=False,
        default="sin_clasificar",
    )
    puntaje_taza: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True,
        comment="Puntaje de catacion en escala SCA (0-100)",
    )
    numero_defectos: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True,
        comment="Numero de granos defectuosos por muestra de 300g (norma FNC)",
    )

    # --- Comercializacion ---
    precio_venta_kg: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    comprador: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    fecha_venta: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    destino_exportacion: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)

    # --- Trazabilidad digital ---
    estado: Mapped[str] = mapped_column(
        Enum(*ESTADOS_LOTE),
        nullable=False,
        default="registrado",
        comment="Estado segun Diagrama de Estados del LOTE",
    )
    hash_integridad: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True,
        comment="SHA-256 calculado al validar. RN-04: detecta alteraciones.",
    )
    codigo_qr: Mapped[Optional[str]] = mapped_column(
        String(300), nullable=True,
        comment="URL publica para escaneo del consumidor (RN-05)",
    )
    validado: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False,
        comment="True cuando el lote pasa a estado 'aprobado'",
    )
    observaciones: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # --- Relaciones ---
    id_cultivo: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("tbl_cultivo.id_cultivo", ondelete="RESTRICT"),
        nullable=False,
        comment="FK a tbl_cultivo - integridad gestionada por MySQL",
    )
    id_usuario_creador: Mapped[int] = mapped_column(Integer, nullable=False)
    fecha_creacion: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    fecha_actualizacion: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, onupdate=lambda: datetime.now(timezone.utc))

    def calcular_hash(self, sal: str = "") -> str:
        """
        RN-04: calcula el hash SHA-256 del registro para
        detectar modificaciones no autorizadas posteriores.
        """
        datos = (
            f"{self.codigo_lote}|{self.variedad_cafe}|"
            f"{self.fecha_cosecha}|{self.kg_cereza_cosechados}|"
            f"{self.clasificacion_calidad}|{self.humedad_final_pct}|"
            f"{self.numero_defectos}|{sal}"
        )
        return hashlib.sha256(datos.encode()).hexdigest()

    def __repr__(self):
        return (
            f"<Lote {self.codigo_lote} estado={self.estado} "
            f"calidad={self.clasificacion_calidad}>"
        )


class EventoTrazabilidad(Base):
    """
    tbl_evento_trazabilidad
    Log inmutable de todos los eventos del ciclo de vida del lote.

    Cada transicion de estado, modificacion administrativa o
    accion relevante genera un evento que no puede eliminarse.
    Implementa el patron de Event Sourcing para cumplir RN-04.
    """
    __tablename__ = "tbl_evento_trazabilidad"

    id_evento: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tipo_evento: Mapped[str] = mapped_column(
        Enum(
            "registro_lote",
            "confirmacion",
            "inicio_secado",
            "lectura_secado",
            "fin_secado",
            "clasificacion_ia",
            "aprobacion",
            "problema_detectado",
            "venta",
            "correccion_admin",
            "eliminacion",
        ),
        nullable=False,
    )
    estado_anterior: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    estado_nuevo: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)
    datos_adicionales: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True,
        comment="JSON con datos especificos del evento",
    )
    id_lote: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("tbl_trazabilidad_lote.id_lote", ondelete="RESTRICT"),
        nullable=False,
    )
    id_usuario: Mapped[int] = mapped_column(Integer, nullable=False)
    fecha_evento: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    ip_origen: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)

    def __repr__(self):
        return (
            f"<Evento {self.tipo_evento} lote={self.id_lote} "
            f"{self.estado_anterior}->{self.estado_nuevo}>"
        )


class ControlSecado(Base):
    """
    tbl_control_secado
    RF-11: monitoreo de temperatura y tiempo durante el proceso
    de secado del cafe pergamino.

    Un lote puede tener multiples lecturas a lo largo de su
    proceso de secado (tipicamente 3 a 15 dias para cafe
    pergamino en Colombia segun CENICAFE).

    Umbrales (CENICAFE - Avance Tecnico 359):
      Temperatura optima: 35-45 C
      Temperatura critica (quema el grano): > 55 C
      Humedad objetivo:   11% +/- 1%
      Tiempo minimo:      72 horas para pergamino natural
    """
    __tablename__ = "tbl_control_secado"

    id_secado: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    temperatura_c: Mapped[float] = mapped_column(
        Float, nullable=False,
        comment="Temperatura del aire de secado en grados Celsius",
    )
    humedad_grano_pct: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True,
        comment="Porcentaje de humedad del grano medido en la lectura",
    )
    humedad_ambiente_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    horas_transcurridas: Mapped[int] = mapped_column(
        Integer, nullable=False,
        comment="Horas totales desde el inicio del secado",
    )
    metodo_secado: Mapped[str] = mapped_column(
        Enum("solar", "mecanico", "mixto"),
        nullable=False,
        default="solar",
    )
    # Alertas calculadas por el servicio
    alerta_temperatura: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    alerta_humedad: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    proceso_completo: Mapped[bool] = mapped_column(
        Boolean, default=False,
        comment="True si la humedad objetivo se ha alcanzado",
    )
    observaciones: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    id_lote: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("tbl_trazabilidad_lote.id_lote", ondelete="CASCADE"),
        nullable=False,
    )
    id_usuario: Mapped[int] = mapped_column(Integer, nullable=False)
    fecha_lectura: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return (
            f"<Secado lote={self.id_lote} T={self.temperatura_c}C "
            f"H={self.humedad_grano_pct}% h={self.horas_transcurridas}h>"
        )


class ClasificacionGrano(Base):
    """
    tbl_clasificacion_grano
    RF-12: resultado de la clasificacion del grano por calidad
    usando criterios de la Federacion Nacional de Cafeteros (FNC)
    y puntaje de taza SCA.

    La clasificacion activa la transicion de estado del lote:
      resultado_aprobado -> 'aprobado' (Diagrama de Estados)
      resultado_defecto  -> 'con_problema'

    Criterios de clasificacion FNC:
      Supremo:      0 defectos, humedad 10-12%
      Excelso Extra: 1-4 defectos
      Excelso:      5-8 defectos
      Corriente:    9-23 defectos
      Pasilla:      > 23 defectos o humedad fuera de rango
    """
    __tablename__ = "tbl_clasificacion_grano"

    id_clasificacion: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    categoria: Mapped[str] = mapped_column(
        Enum("supremo", "excelso_extra", "excelso", "corriente", "pasilla"),
        nullable=False,
    )
    numero_defectos: Mapped[int] = mapped_column(Integer, nullable=False)
    humedad_pct: Mapped[float] = mapped_column(Float, nullable=False)
    puntaje_taza: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True,
        comment="Puntaje SCA: >= 80 = specialty coffee",
    )
    factores_calidad: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True,
        comment='JSON: ["fragancia_9.0","acidez_8.5","cuerpo_8.0"]',
    )
    observaciones_calidad: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    precio_sugerido_kg: Mapped[Optional[float]] = mapped_column(
        Numeric(10, 2), nullable=True,
        comment="Precio sugerido en COP por kg segun categoria",
    )
    aprobado_exportacion: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False,
        comment="True si cumple estandares FNC para exportacion",
    )
    # Metodo de clasificacion usado
    metodo: Mapped[str] = mapped_column(
        Enum("ia_automatica", "manual", "laboratorio"),
        nullable=False,
        default="ia_automatica",
    )
    confianza_ia: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    version_modelo_ia: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    id_lote: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("tbl_trazabilidad_lote.id_lote", ondelete="CASCADE"),
        nullable=False,
    )
    id_usuario: Mapped[int] = mapped_column(Integer, nullable=False)
    fecha_clasificacion: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return (
            f"<Clasificacion lote={self.id_lote} "
            f"cat={self.categoria} defectos={self.numero_defectos}>"
        )
