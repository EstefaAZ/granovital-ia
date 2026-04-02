# ==============================================================
# modulo_02_cultivos / app/services/cultivo_service.py
# Logica de negocio - Cultivos, Lotes y Sensores
#
# Reglas implementadas:
#   RN-02  Todo lote debe tener trazabilidad completa antes
#          de pasar al estado 'vendido'
#   RNF-05 Integridad - eliminacion logica (no fisica)
#   RNF-06 Soporte para nuevos sensores IoT sin cambios de schema
#
# Casos de prueba cubiertos:
#   CP-03  Registro cultivo
#   CP-04  Registro lote
# ==============================================================

import secrets
import logging
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.models.cultivo import Cultivo, Lote, Sensor
from app.schemas.cultivo import (
    CultivoCreate, CultivoUpdate,
    LoteCreate, LoteUpdate,
    SensorCreate,
    ResumenCultivoResponse,
)

logger = logging.getLogger(__name__)


# ==============================================================
# TRANSICIONES VALIDAS DE ESTADO
# Implementa las reglas del diagrama de estados oficial
# ==============================================================

TRANSICIONES_CULTIVO = {
    "creado":                  {"en_seguimiento", "eliminado"},
    "en_seguimiento":          {"con_problema_detectado", "finalizado", "eliminado"},
    "con_problema_detectado":  {"tratamiento_aplicado", "en_seguimiento"},
    "tratamiento_aplicado":    {"en_seguimiento", "finalizado"},
    "finalizado":              set(),
    "eliminado":               set(),
}

TRANSICIONES_LOTE = {
    "registrado":   {"disponible", "eliminado"},
    "disponible":   {"en_analisis", "eliminado"},
    "en_analisis":  {"aprobado", "con_problema"},
    "aprobado":     {"vendido"},
    "con_problema": {"en_analisis", "eliminado"},
    "vendido":      set(),
    "eliminado":    set(),
}


class CultivoService:
    """Servicio principal para gestion de cultivos y lotes."""

    def __init__(self, db: Session):
        self.db = db

    # ----------------------------------------------------------
    # CULTIVOS - RF-03
    # ----------------------------------------------------------

    def crear_cultivo(
        self, datos: CultivoCreate, usuario_id: int
    ) -> Cultivo:
        """
        CP-03: registra un nuevo cultivo en estado 'creado'.
        Vincula el cultivo al usuario autenticado.
        """
        cultivo = Cultivo(
            nombre_cultivo=datos.nombre_cultivo,
            ubicacion=datos.ubicacion,
            area_hectareas=datos.area_hectareas,
            variedad_cafe=datos.variedad_cafe,
            fecha_siembra=datos.fecha_siembra,
            observaciones=datos.observaciones,
            estado="creado",
            id_usuario=usuario_id,
        )
        self.db.add(cultivo)
        self.db.commit()
        self.db.refresh(cultivo)
        logger.info(
            f"Cultivo creado: id={cultivo.id_cultivo} "
            f"nombre='{cultivo.nombre_cultivo}' usuario={usuario_id}"
        )
        return cultivo

    def listar_cultivos(self, usuario_id: int) -> List[Cultivo]:
        """
        Retorna los cultivos activos del usuario autenticado.
        No incluye cultivos en estado 'eliminado'.
        """
        return (
            self.db.query(Cultivo)
            .filter(
                Cultivo.id_usuario == usuario_id,
                Cultivo.estado != "eliminado",
            )
            .order_by(Cultivo.fecha_registro.desc())
            .all()
        )

    def obtener_cultivo(
        self, cultivo_id: int, usuario_id: int
    ) -> Cultivo:
        """
        Retorna un cultivo verificando la propiedad del usuario.
        Lanza HTTP 404 si no existe o no pertenece al usuario.
        """
        cultivo = (
            self.db.query(Cultivo)
            .filter(
                Cultivo.id_cultivo == cultivo_id,
                Cultivo.id_usuario == usuario_id,
                Cultivo.estado != "eliminado",
            )
            .first()
        )
        if not cultivo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=(
                    f"Cultivo con id={cultivo_id} no encontrado "
                    "o no tiene acceso a este recurso"
                ),
            )
        return cultivo

    def actualizar_cultivo(
        self, cultivo_id: int, datos: CultivoUpdate, usuario_id: int
    ) -> Cultivo:
        """
        Actualiza los datos de un cultivo.
        Valida la transicion de estado contra el diagrama de estados oficial.
        """
        cultivo = self.obtener_cultivo(cultivo_id, usuario_id)

        if datos.estado:
            self._validar_transicion_cultivo(cultivo.estado, datos.estado)

        campos = datos.model_dump(exclude_unset=True)
        for campo, valor in campos.items():
            setattr(cultivo, campo, valor)

        self.db.commit()
        self.db.refresh(cultivo)
        logger.info(
            f"Cultivo actualizado: id={cultivo_id} "
            f"estado='{cultivo.estado}'"
        )
        return cultivo

    def eliminar_cultivo(
        self, cultivo_id: int, usuario_id: int
    ) -> None:
        """
        RNF-05: eliminacion logica. El cultivo pasa a estado 'eliminado'.
        No se borra el registro fisico de la base de datos.
        """
        cultivo = self.obtener_cultivo(cultivo_id, usuario_id)
        cultivo.estado = "eliminado"
        self.db.commit()
        logger.info(f"Cultivo eliminado (logico): id={cultivo_id}")

    def resumen_dashboard(self, usuario_id: int) -> ResumenCultivoResponse:
        """
        Genera el resumen estadistico para el panel principal
        del Caficultor con una sola consulta agregada.
        """
        cultivos_activos = (
            self.db.query(func.count(Cultivo.id_cultivo))
            .filter(
                Cultivo.id_usuario == usuario_id,
                Cultivo.estado != "eliminado",
            )
            .scalar() or 0
        )

        area_total = (
            self.db.query(func.sum(Cultivo.area_hectareas))
            .filter(
                Cultivo.id_usuario == usuario_id,
                Cultivo.estado != "eliminado",
            )
            .scalar() or 0.0
        )

        # Subquery para obtener lotes de los cultivos del usuario
        ids_cultivos = (
            self.db.query(Cultivo.id_cultivo)
            .filter(Cultivo.id_usuario == usuario_id)
            .subquery()
        )

        total_lotes = (
            self.db.query(func.count(Lote.id_lote))
            .filter(Lote.id_cultivo.in_(ids_cultivos))
            .scalar() or 0
        )

        lotes_en_proceso = (
            self.db.query(func.count(Lote.id_lote))
            .filter(
                Lote.id_cultivo.in_(ids_cultivos),
                Lote.estado_lote.in_(["registrado", "disponible", "en_analisis"]),
            )
            .scalar() or 0
        )

        lotes_vendidos = (
            self.db.query(func.count(Lote.id_lote))
            .filter(
                Lote.id_cultivo.in_(ids_cultivos),
                Lote.estado_lote == "vendido",
            )
            .scalar() or 0
        )

        lotes_con_problema = (
            self.db.query(func.count(Lote.id_lote))
            .filter(
                Lote.id_cultivo.in_(ids_cultivos),
                Lote.estado_lote == "con_problema",
            )
            .scalar() or 0
        )

        return ResumenCultivoResponse(
            total_cultivos_activos=cultivos_activos,
            total_lotes=total_lotes,
            lotes_en_proceso=lotes_en_proceso,
            lotes_vendidos=lotes_vendidos,
            lotes_con_problema=lotes_con_problema,
            area_total_hectareas=float(area_total),
        )

    # ----------------------------------------------------------
    # LOTES - RF-04
    # ----------------------------------------------------------

    def crear_lote(
        self, cultivo_id: int, datos: LoteCreate, usuario_id: int
    ) -> Lote:
        """
        CP-04: registra un nuevo lote en estado 'registrado'.
        Genera automaticamente el codigo QR para consulta publica (RF-15).
        Verifica que el usuario sea propietario del cultivo.
        """
        self.obtener_cultivo(cultivo_id, usuario_id)

        existente = self.db.query(Lote).filter(
            Lote.codigo_lote == datos.codigo_lote
        ).first()
        if existente:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Ya existe un lote con el codigo '{datos.codigo_lote}'. "
                    "Use un codigo unico para este lote."
                ),
            )

        # Genera token URL-safe de 48 chars para el QR
        codigo_qr = secrets.token_urlsafe(36)

        lote = Lote(
            codigo_lote=datos.codigo_lote,
            codigo_qr=codigo_qr,
            fecha_cosecha=datos.fecha_cosecha,
            cantidad_kg=datos.cantidad_kg,
            observaciones=datos.observaciones,
            estado_lote="registrado",
            id_cultivo=cultivo_id,
        )
        self.db.add(lote)
        self.db.commit()
        self.db.refresh(lote)
        logger.info(
            f"Lote creado: id={lote.id_lote} "
            f"codigo='{lote.codigo_lote}' cultivo={cultivo_id}"
        )
        return lote

    def listar_lotes(
        self, cultivo_id: int, usuario_id: int
    ) -> List[Lote]:
        """Retorna los lotes del cultivo que pertenece al usuario."""
        self.obtener_cultivo(cultivo_id, usuario_id)
        return (
            self.db.query(Lote)
            .filter(
                Lote.id_cultivo == cultivo_id,
                Lote.estado_lote != "eliminado",
            )
            .order_by(Lote.fecha_registro.desc())
            .all()
        )

    def obtener_lote(
        self, lote_id: int, usuario_id: int
    ) -> Lote:
        """Obtiene un lote verificando la cadena de propiedad usuario-cultivo."""
        lote = (
            self.db.query(Lote)
            .join(Cultivo)
            .filter(
                Lote.id_lote == lote_id,
                Cultivo.id_usuario == usuario_id,
                Lote.estado_lote != "eliminado",
            )
            .first()
        )
        if not lote:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Lote con id={lote_id} no encontrado o sin acceso",
            )
        return lote

    def actualizar_lote(
        self, lote_id: int, datos: LoteUpdate, usuario_id: int
    ) -> Lote:
        """
        Actualiza el estado u observaciones de un lote.
        RN-02: bloquea el paso a 'vendido' si no hay trazabilidad completa.
        Valida transiciones segun el diagrama de estados del Lote.
        """
        lote = self.obtener_lote(lote_id, usuario_id)

        if datos.estado_lote:
            self._validar_transicion_lote(lote.estado_lote, datos.estado_lote)

            if datos.estado_lote == "vendido":
                self._verificar_trazabilidad_rn02(lote_id)

            lote.estado_lote = datos.estado_lote

        if datos.cantidad_kg is not None:
            lote.cantidad_kg = datos.cantidad_kg
        if datos.observaciones is not None:
            lote.observaciones = datos.observaciones

        self.db.commit()
        self.db.refresh(lote)
        logger.info(
            f"Lote actualizado: id={lote_id} estado='{lote.estado_lote}'"
        )
        return lote

    def eliminar_lote(
        self, lote_id: int, usuario_id: int
    ) -> None:
        """RNF-05: eliminacion logica del lote."""
        lote = self.obtener_lote(lote_id, usuario_id)
        lote.estado_lote = "eliminado"
        self.db.commit()
        logger.info(f"Lote eliminado (logico): id={lote_id}")

    # ----------------------------------------------------------
    # SENSORES - RNF-06, RNF-09
    # ----------------------------------------------------------

    def registrar_sensor(
        self, cultivo_id: int, datos: SensorCreate, usuario_id: int
    ) -> Sensor:
        """
        RNF-06: registra un nuevo sensor IoT sin cambios de arquitectura.
        El sensor queda vinculado al cultivo y empieza en estado 'activo'.
        """
        self.obtener_cultivo(cultivo_id, usuario_id)

        existente = self.db.query(Sensor).filter(
            Sensor.codigo_sensor == datos.codigo_sensor
        ).first()
        if existente:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Ya existe un sensor con codigo '{datos.codigo_sensor}'",
            )

        sensor = Sensor(
            codigo_sensor=datos.codigo_sensor,
            tipo_sensor=datos.tipo_sensor,
            descripcion=datos.descripcion,
            unidad_medida=datos.unidad_medida,
            fecha_instalacion=datos.fecha_instalacion,
            estado="activo",
            id_cultivo=cultivo_id,
        )
        self.db.add(sensor)
        self.db.commit()
        self.db.refresh(sensor)
        logger.info(
            f"Sensor registrado: codigo='{sensor.codigo_sensor}' "
            f"tipo='{sensor.tipo_sensor}' cultivo={cultivo_id}"
        )
        return sensor

    def listar_sensores(
        self, cultivo_id: int, usuario_id: int
    ) -> List[Sensor]:
        self.obtener_cultivo(cultivo_id, usuario_id)
        return (
            self.db.query(Sensor)
            .filter(Sensor.id_cultivo == cultivo_id)
            .order_by(Sensor.codigo_sensor)
            .all()
        )

    # ----------------------------------------------------------
    # METODOS PRIVADOS
    # ----------------------------------------------------------

    def _validar_transicion_cultivo(
        self, estado_actual: str, estado_nuevo: str
    ) -> None:
        """
        Valida que la transicion de estado del cultivo sea
        coherente con el diagrama de estados oficial del proyecto.
        """
        permitidos = TRANSICIONES_CULTIVO.get(estado_actual, set())
        if estado_nuevo not in permitidos:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"Transicion invalida en el cultivo: "
                    f"'{estado_actual}' no puede cambiar a '{estado_nuevo}'. "
                    f"Transiciones permitidas: {sorted(permitidos)}"
                ),
            )

    def _validar_transicion_lote(
        self, estado_actual: str, estado_nuevo: str
    ) -> None:
        """
        Valida que la transicion de estado del lote sea coherente
        con el diagrama de estados oficial del proyecto.
        """
        permitidos = TRANSICIONES_LOTE.get(estado_actual, set())
        if estado_nuevo not in permitidos:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"Transicion invalida en el lote: "
                    f"'{estado_actual}' no puede cambiar a '{estado_nuevo}'. "
                    f"Transiciones permitidas: {sorted(permitidos)}"
                ),
            )

    def _verificar_trazabilidad_rn02(self, lote_id: int) -> None:
        """
        RN-02: verifica que el lote tenga registrada la etapa
        'comercializacion' en tbl_trazabilidad antes de pasar a 'vendido'.
        Lanza HTTP 422 si la condicion no se cumple.
        """
        resultado = self.db.execute(
            text(
                "SELECT COUNT(*) FROM tbl_trazabilidad_lote "
                "WHERE id_lote = :lote_id AND estado IN ('aprobado','vendido')"  -- BUG-023 FIX
            ),
            {"lote_id": lote_id},
        ).scalar()

        if not resultado:
            logger.warning(
                f"RN-02 bloqueado: lote={lote_id} intento pasar a 'vendido' "
                "sin trazabilidad completa"
            )
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "RN-02: Este lote no puede marcarse como 'vendido' todavia. "
                    "El lote debe estar aprobado o vendido en trazabilidad antes de comercializar. "
                    "en el modulo de Trazabilidad."
                ),
            )
