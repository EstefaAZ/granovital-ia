# ==============================================================
# modulo_05_trazabilidad / app/services/trazabilidad_service.py
# Servicio principal — Orquesta trazabilidad, secado y clasificacion
#
# Implementa:
#   RF-10  CRUD de lotes y ciclo de vida completo
#   RF-11  Control de secado con alertas agronomicas
#   RF-12  Clasificacion del grano con logica FNC
#   RF-15  Consulta publica via codigo de lote (RN-05)
#   RN-02  Validacion de completitud antes de comercializar
#   RN-04  Bloqueo de modificaciones en lotes validados
#   RNF-05 Generacion y verificacion de hash de integridad
#
# DIAGRAMA DE ESTADOS del LOTE implementado en _transicionar():
#   registrado -> disponible     (confirmarRegistro)
#   disponible -> en_analisis    (enviarAAnalisis)
#   en_analisis -> aprobado      (resultadoIA: aprobado)
#   en_analisis -> con_problema  (resultadoIA: defecto)
#   aprobado    -> vendido       (ventaRealizada)
#   con_problema -> en_analisis  (reclasificar)
# ==============================================================

import json
import logging
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.trazabilidad import (
    ClasificacionGrano, ControlSecado,
    EventoTrazabilidad, TrazabilidadLote,
)
from app.schemas.trazabilidad import (
    ClasificacionCreate, ClasificacionResponse,
    EventoResponse, LoteCreate, LotePublicoResponse,
    LoteResponse, LoteUpdate, ResumenSecadoResponse,
    SecadoCreate, SecadoResponse, TransicionEstadoResponse,
)
from app.util.qr_generator import generar_url_qr, generar_svg_qr

logger = logging.getLogger(__name__)


# ==============================================================
# MOTOR DE CLASIFICACION FNC (RF-12)
# Criterios: Norma de calidad FNC / NTC 2 cafe pergamino seco
# ==============================================================

CATEGORIAS_FNC = {
    "supremo":       {"defectos_max": 0,  "precio_base": 6500},
    "excelso_extra": {"defectos_max": 4,  "precio_base": 5800},
    "excelso":       {"defectos_max": 8,  "precio_base": 5200},
    "corriente":     {"defectos_max": 23, "precio_base": 4500},
    "pasilla":       {"defectos_max": 999,"precio_base": 3000},
}

DESCRIPCIONES_CATEGORIA = {
    "supremo":       "Cafe Supremo — maxima calidad, cero defectos, taza excepcional",
    "excelso_extra": "Cafe Excelso Extra — alta calidad, minimos defectos",
    "excelso":       "Cafe Excelso — calidad estandar de exportacion FNC",
    "corriente":     "Cafe Corriente — calidad aceptable para mercado nacional",
    "pasilla":       "Cafe Pasilla — calidad inferior, requiere reclasificacion",
}

MENSAJES_CALIDAD_PUBLICA = {
    "supremo":       "Este cafe es de la mas alta calidad. Cosechado y procesado con maxima dedicacion.",
    "excelso_extra": "Este cafe cumple los mas altos estandares de exportacion de Colombia.",
    "excelso":       "Este cafe cumple los estandares de exportacion de la Federacion Nacional de Cafeteros.",
    "corriente":     "Cafe de calidad estandar, cultivado con practicas tradicionales colombianas.",
    "pasilla":       "Cafe en proceso de mejora de calidad.",
    "sin_clasificar": "Este lote aun no ha sido clasificado.",
}

PRECIOS_SUGERIDOS = {
    "supremo":       7200.0,
    "excelso_extra": 6100.0,
    "excelso":       5400.0,
    "corriente":     4600.0,
    "pasilla":       3100.0,
}


def _clasificar_grano_fnc(
    numero_defectos: int,
    humedad_pct:     float,
    puntaje_taza:    Optional[float],
) -> Tuple[str, bool, Optional[float]]:
    """
    Clasifica el grano segun la norma FNC.
    Retorna (categoria, aprobado_exportacion, precio_sugerido).
    """
    # Humedad fuera del rango aceptable -> pasilla
    if humedad_pct > settings.HUMEDAD_MAX_EXPORTACION + 3 or humedad_pct < 8.0:
        return "pasilla", False, PRECIOS_SUGERIDOS["pasilla"]

    # Clasificar por defectos
    if numero_defectos == 0:
        categoria = "supremo"
    elif numero_defectos <= settings.DEFECTOS_MAX_EXTRA:
        categoria = "excelso_extra"
    elif numero_defectos <= settings.DEFECTOS_MAX_EXCELSO:
        categoria = "excelso"
    elif numero_defectos <= 23:
        categoria = "corriente"
    else:
        categoria = "pasilla"

    # Penalizar por humedad alta (no descarta pero baja categoria)
    if humedad_pct > settings.HUMEDAD_MAX_EXPORTACION:
        DESCENSO = {"supremo": "excelso_extra", "excelso_extra": "excelso",
                    "excelso": "corriente", "corriente": "pasilla", "pasilla": "pasilla"}
        categoria = DESCENSO.get(categoria, categoria)

    aprobado = categoria in ("supremo", "excelso_extra", "excelso")

    # Bonus por puntaje de taza (specialty coffee >= 80 SCA)
    precio = PRECIOS_SUGERIDOS.get(categoria, 4000.0)
    if puntaje_taza and puntaje_taza >= 80.0:
        precio *= 1.15   # +15% specialty coffee premium

    return categoria, aprobado, round(precio, 2)


# ==============================================================
# SERVICIO PRINCIPAL
# ==============================================================

class TrazabilidadService:

    def __init__(self, db: Session):
        self.db = db

    # ----------------------------------------------------------
    # UTILIDADES
    # ----------------------------------------------------------

    def _verificar_acceso_lote(
        self, id_lote: int, usuario_id: int, es_admin: bool = False
    ) -> TrazabilidadLote:
        """
        Recupera el lote verificando propiedad.
        Admins pueden acceder a cualquier lote.
        """
        lote = (
            self.db.query(TrazabilidadLote)
            .filter(TrazabilidadLote.id_lote == id_lote)
            .first()
        )
        if not lote:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Lote {id_lote} no encontrado.",
            )
        if not es_admin and lote.id_usuario_creador != usuario_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tiene acceso a este lote.",
            )
        return lote

    def _verificar_cultivo(self, id_cultivo: int, usuario_id: int) -> None:
        r = self.db.execute(
            text(
                "SELECT id_cultivo FROM tbl_cultivo "
                "WHERE id_cultivo = :c AND id_usuario = :u AND estado != 'eliminado'"
            ),
            {"c": id_cultivo, "u": usuario_id},
        ).fetchone()
        if not r:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Cultivo {id_cultivo} no encontrado o sin acceso.",
            )

    def _registrar_evento(
        self,
        lote:             TrazabilidadLote,
        tipo:             str,
        descripcion:      str,
        usuario_id:       int,
        estado_anterior:  Optional[str] = None,
        estado_nuevo:     Optional[str] = None,
        datos_adicionales: Optional[dict] = None,
    ) -> None:
        """Persiste un evento inmutable en el log de trazabilidad."""
        evento = EventoTrazabilidad(
            tipo_evento       = tipo,
            estado_anterior   = estado_anterior,
            estado_nuevo      = estado_nuevo,
            descripcion       = descripcion,
            datos_adicionales = json.dumps(datos_adicionales or {}, ensure_ascii=False),
            id_lote           = lote.id_lote,
            id_usuario        = usuario_id,
        )
        self.db.add(evento)

    def _verificar_rn04(
        self, lote: TrazabilidadLote, usuario_id: int, es_admin: bool
    ) -> None:
        """
        RN-04: bloquea modificaciones si el lote esta validado
        y el solicitante no es Administrador.
        """
        if lote.validado and not es_admin:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"RN-04: El lote '{lote.codigo_lote}' esta validado "
                    f"(estado: {lote.estado}) y no puede ser modificado. "
                    "Solo el Administrador puede hacer correcciones."
                ),
            )

    def _generar_codigo_lote(self) -> str:
        """Genera codigo legible unico: GV-AAAA-NNNN."""
        anio   = datetime.now().year
        ultimo = self.db.execute(
            text("SELECT COUNT(*) as cnt FROM tbl_trazabilidad_lote")
        ).fetchone()
        num = (ultimo.cnt + 1) if ultimo else 1
        return f"GV-{anio}-{num:04d}"

    # ----------------------------------------------------------
    # RF-10 — CRUD DE LOTES
    # ----------------------------------------------------------

    def crear_lote(self, datos: LoteCreate, usuario_id: int) -> LoteResponse:
        """
        CP-04: Registrar lote. Implementa el paso 'registrarLote'
        del Diagrama de Estados (estado inicial: 'registrado').
        """
        self._verificar_cultivo(datos.id_cultivo, usuario_id)

        codigo = self._generar_codigo_lote()
        lote   = TrazabilidadLote(
            codigo_lote          = codigo,
            variedad_cafe        = datos.variedad_cafe,
            fecha_cosecha        = datos.fecha_cosecha,
            metodo_cosecha       = datos.metodo_cosecha,
            kg_cereza_cosechados = datos.kg_cereza_cosechados,
            metodo_beneficio     = datos.metodo_beneficio,
            observaciones        = datos.observaciones,
            id_cultivo           = datos.id_cultivo,
            id_usuario_creador   = usuario_id,
            estado               = "registrado",
        )
        self.db.add(lote)
        self.db.flush()

        self._registrar_evento(
            lote, "registro_lote",
            f"Lote {codigo} registrado con {datos.kg_cereza_cosechados} kg de cereza.",
            usuario_id,
            estado_nuevo="registrado",
            datos_adicionales={"variedad": datos.variedad_cafe, "kg": float(datos.kg_cereza_cosechados)},
        )

        self.db.commit()
        self.db.refresh(lote)
        logger.info(f"Lote creado: {codigo} usuario={usuario_id}")
        return self._lote_a_response(lote)

    def listar_lotes(
        self, usuario_id: int, cultivo_id: Optional[int] = None
    ) -> List[LoteResponse]:
        q = self.db.query(TrazabilidadLote).filter(
            TrazabilidadLote.id_usuario_creador == usuario_id,
            TrazabilidadLote.estado             != "eliminado",
        )
        if cultivo_id:
            q = q.filter(TrazabilidadLote.id_cultivo == cultivo_id)
        lotes = q.order_by(TrazabilidadLote.fecha_creacion.desc()).all()
        return [self._lote_a_response(l) for l in lotes]

    def obtener_lote(self, id_lote: int, usuario_id: int) -> LoteResponse:
        lote = self._verificar_acceso_lote(id_lote, usuario_id)
        return self._lote_a_response(lote)

    def actualizar_lote(
        self,
        id_lote:    int,
        datos:      LoteUpdate,
        usuario_id: int,
        es_admin:   bool = False,
    ) -> LoteResponse:
        """
        Actualiza campos operativos del lote.
        RN-04: bloquea si el lote esta validado y el usuario no es admin.
        """
        lote = self._verificar_acceso_lote(id_lote, usuario_id, es_admin)
        self._verificar_rn04(lote, usuario_id, es_admin)

        campos = datos.model_dump(exclude_none=True)
        for k, v in campos.items():
            setattr(lote, k, v)

        tipo_evento = "correccion_admin" if es_admin else "confirmacion"
        self._registrar_evento(
            lote, tipo_evento,
            f"Campos actualizados: {', '.join(campos.keys())}",
            usuario_id,
            datos_adicionales={"campos_modificados": list(campos.keys())},
        )
        self.db.commit()
        self.db.refresh(lote)
        return self._lote_a_response(lote)

    def confirmar_lote(self, id_lote: int, usuario_id: int) -> TransicionEstadoResponse:
        """
        Diagrama de Estados: Registrado -> Disponible.
        Ejecuta 'confirmarRegistro'.
        """
        lote = self._verificar_acceso_lote(id_lote, usuario_id)
        if lote.estado != "registrado":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Solo lotes en estado 'registrado' pueden confirmarse. Estado actual: {lote.estado}",
            )
        anterior = lote.estado
        lote.estado = "disponible"
        self._registrar_evento(
            lote, "confirmacion",
            "Lote confirmado y disponible para proceso de secado y analisis.",
            usuario_id, anterior, "disponible",
        )
        self.db.commit()
        return TransicionEstadoResponse(
            id_lote=id_lote, codigo_lote=lote.codigo_lote,
            estado_anterior=anterior, estado_nuevo="disponible",
            mensaje="Lote confirmado. Puede iniciar el control de secado.",
        )

    def registrar_venta(
        self, id_lote: int, usuario_id: int,
        comprador: str, precio_kg: float,
        destino: Optional[str] = None,
    ) -> TransicionEstadoResponse:
        """
        RN-02: verifica trazabilidad completa antes de registrar la venta.
        Diagrama: Aprobado -> Vendido.
        """
        lote = self._verificar_acceso_lote(id_lote, usuario_id)

        if lote.estado != "aprobado":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"RN-02: Solo lotes en estado 'aprobado' pueden venderse. "
                    f"Estado actual: '{lote.estado}'. "
                    "Complete el proceso de clasificacion primero."
                ),
            )

        # RN-02: verificar que el lote tiene trazabilidad completa
        if not lote.clasificacion_calidad or lote.clasificacion_calidad == "sin_clasificar":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "RN-02: El lote no tiene clasificacion de calidad. "
                    "Ejecute la clasificacion del grano antes de comercializar."
                ),
            )

        anterior           = lote.estado
        lote.estado        = "vendido"
        lote.comprador     = comprador
        lote.precio_venta_kg = precio_kg
        lote.destino_exportacion = destino
        lote.fecha_venta   = datetime.utcnow()

        self._registrar_evento(
            lote, "venta",
            f"Lote vendido a '{comprador}' por ${precio_kg}/kg.",
            usuario_id, anterior, "vendido",
            datos_adicionales={"comprador": comprador, "precio_kg": precio_kg},
        )
        self.db.commit()
        return TransicionEstadoResponse(
            id_lote=id_lote, codigo_lote=lote.codigo_lote,
            estado_anterior=anterior, estado_nuevo="vendido",
            mensaje=f"Venta registrada. Lote vendido a {comprador}.",
        )

    # ----------------------------------------------------------
    # RF-11 — CONTROL DE SECADO
    # ----------------------------------------------------------

    def registrar_lectura_secado(
        self, id_lote: int, datos: SecadoCreate, usuario_id: int
    ) -> SecadoResponse:
        """
        RF-11: registra una lectura de temperatura y humedad
        durante el proceso de secado del lote.
        Calcula alertas con base en umbrales CENICAFE.
        """
        lote = self._verificar_acceso_lote(id_lote, usuario_id)

        if lote.estado == "eliminado":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="No se puede registrar secado en un lote eliminado.",
            )

        # Transicion automatica a en_analisis si el lote esta disponible
        if lote.estado == "disponible":
            lote.estado = "en_analisis"

        # Calcular alertas
        alerta_temp   = self._alerta_temperatura_secado(datos.temperatura_c)
        alerta_hum    = self._alerta_humedad_secado(datos.humedad_grano_pct)
        proceso_ok    = (
            datos.humedad_grano_pct is not None
            and datos.humedad_grano_pct <= settings.SECADO_HUMEDAD_OBJETIVO
            and datos.horas_transcurridas >= settings.SECADO_HORAS_MINIMAS
        )

        registro = ControlSecado(
            temperatura_c        = datos.temperatura_c,
            humedad_grano_pct    = datos.humedad_grano_pct,
            humedad_ambiente_pct = datos.humedad_ambiente_pct,
            horas_transcurridas  = datos.horas_transcurridas,
            metodo_secado        = datos.metodo_secado,
            alerta_temperatura   = alerta_temp,
            alerta_humedad       = alerta_hum,
            proceso_completo     = proceso_ok,
            observaciones        = datos.observaciones,
            id_lote              = id_lote,
            id_usuario           = usuario_id,
        )
        self.db.add(registro)

        # Actualizar humedad final en el lote si el secado concluyo
        if proceso_ok and datos.humedad_grano_pct:
            lote.humedad_final_pct = datos.humedad_grano_pct
            lote.fecha_fin_secado  = datetime.utcnow()

        self._registrar_evento(
            lote, "lectura_secado" if not proceso_ok else "fin_secado",
            f"Temperatura {datos.temperatura_c}C, humedad {datos.humedad_grano_pct}%, "
            f"hora {datos.horas_transcurridas}h.",
            usuario_id,
        )

        self.db.commit()
        self.db.refresh(registro)

        # Calcular progreso hacia humedad objetivo
        progreso = None
        if datos.humedad_grano_pct is not None:
            hu_inicial = 50.0   # humedad inicial tipica cafe recien despulpado
            rango      = hu_inicial - settings.SECADO_HUMEDAD_OBJETIVO
            avance     = hu_inicial - datos.humedad_grano_pct
            progreso   = min(100.0, round(avance / rango * 100, 1)) if rango > 0 else 0

        return SecadoResponse(
            id_secado            = registro.id_secado,
            temperatura_c        = registro.temperatura_c,
            humedad_grano_pct    = registro.humedad_grano_pct,
            humedad_ambiente_pct = registro.humedad_ambiente_pct,
            horas_transcurridas  = registro.horas_transcurridas,
            metodo_secado        = registro.metodo_secado,
            alerta_temperatura   = alerta_temp,
            alerta_humedad       = alerta_hum,
            proceso_completo     = proceso_ok,
            progreso_humedad_pct = progreso,
            observaciones        = registro.observaciones,
            id_lote              = id_lote,
            fecha_lectura        = registro.fecha_lectura,
        )

    def resumen_secado(self, id_lote: int, usuario_id: int) -> ResumenSecadoResponse:
        """RF-11: resumen del proceso de secado de un lote."""
        lote     = self._verificar_acceso_lote(id_lote, usuario_id)
        lecturas = (
            self.db.query(ControlSecado)
            .filter(ControlSecado.id_lote == id_lote)
            .order_by(ControlSecado.horas_transcurridas)
            .all()
        )

        if not lecturas:
            return ResumenSecadoResponse(
                id_lote=id_lote, codigo_lote=lote.codigo_lote,
                total_lecturas=0, horas_totales=0,
                humedad_objetivo=settings.SECADO_HUMEDAD_OBJETIVO,
                proceso_completo=False, cumple_horas_minimas=False,
                alertas_activas=[],
                recomendacion="Sin lecturas de secado registradas. Inicie el monitoreo.",
            )

        ultima        = lecturas[-1]
        horas_totales = ultima.horas_transcurridas
        temps         = [l.temperatura_c for l in lecturas]
        temp_prom     = round(sum(temps) / len(temps), 1)
        alertas       = [l.alerta_temperatura for l in lecturas if l.alerta_temperatura]
        alertas      += [l.alerta_humedad      for l in lecturas if l.alerta_humedad]
        proceso_ok    = any(l.proceso_completo for l in lecturas)
        cumple_horas  = horas_totales >= settings.SECADO_HORAS_MINIMAS

        if proceso_ok:
            reco = "Proceso de secado completado. Proceda con la clasificacion del grano (RF-12)."
        elif not cumple_horas:
            faltantes = settings.SECADO_HORAS_MINIMAS - horas_totales
            reco = f"Faltan {faltantes}h para cumplir el minimo de {settings.SECADO_HORAS_MINIMAS}h. Continue el secado."
        else:
            reco = "Horas minimas cumplidas. Verifique que la humedad llegue al objetivo del 11%."

        return ResumenSecadoResponse(
            id_lote=id_lote, codigo_lote=lote.codigo_lote,
            total_lecturas=len(lecturas), horas_totales=horas_totales,
            temp_promedio=temp_prom,
            temp_ultima=ultima.temperatura_c,
            humedad_actual=ultima.humedad_grano_pct,
            humedad_objetivo=settings.SECADO_HUMEDAD_OBJETIVO,
            proceso_completo=proceso_ok,
            cumple_horas_minimas=cumple_horas,
            alertas_activas=list(set(alertas)),
            recomendacion=reco,
        )

    # ----------------------------------------------------------
    # RF-12 — CLASIFICACION DEL GRANO
    # ----------------------------------------------------------

    def clasificar_grano(
        self, id_lote: int, datos: ClasificacionCreate, usuario_id: int
    ) -> ClasificacionResponse:
        """
        RF-12: clasifica el grano y genera la transicion de estado
        del lote (Diagrama de Estados):
          resultado aprobado -> estado 'aprobado'
          resultado defecto  -> estado 'con_problema'

        Tambien:
          - Calcula hash de integridad (RN-04)
          - Genera la URL del QR publico (RN-05)
          - Valida que el lote haya completado el secado (RN-02)
        """
        lote = self._verificar_acceso_lote(id_lote, usuario_id)

        if lote.estado == "eliminado":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="No se puede clasificar un lote eliminado.",
            )

        # El lote debe estar en proceso antes de clasificar
        if lote.estado not in ("disponible", "en_analisis", "con_problema"):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"El lote en estado '{lote.estado}' no puede clasificarse. "
                    "Solo lotes en proceso (disponible, en_analisis, con_problema) "
                    "pueden ser clasificados."
                ),
            )

        # Clasificar con logica FNC
        categoria, aprobado, precio = _clasificar_grano_fnc(
            datos.numero_defectos,
            datos.humedad_pct,
            datos.puntaje_taza,
        )

        confianza = 0.92 if datos.metodo == "ia_automatica" else 1.0

        clasificacion = ClasificacionGrano(
            categoria              = categoria,
            numero_defectos        = datos.numero_defectos,
            humedad_pct            = datos.humedad_pct,
            puntaje_taza           = datos.puntaje_taza,
            factores_calidad       = datos.factores_calidad,
            observaciones_calidad  = datos.observaciones_calidad,
            precio_sugerido_kg     = precio,
            aprobado_exportacion   = aprobado,
            metodo                 = datos.metodo,
            confianza_ia           = confianza,
            version_modelo_ia      = "fnc-reglas-1.0",
            id_lote                = id_lote,
            id_usuario             = usuario_id,
        )
        self.db.add(clasificacion)

        # Actualizar el lote con los resultados
        anterior                      = lote.estado
        lote.clasificacion_calidad    = categoria
        lote.humedad_final_pct        = datos.humedad_pct
        lote.numero_defectos          = datos.numero_defectos
        lote.puntaje_taza             = datos.puntaje_taza

        # Transicion de estado (Diagrama de Estados)
        if aprobado:
            lote.estado   = "aprobado"
            lote.validado = True

            # RN-04: generar hash de integridad al validar
            lote.hash_integridad = lote.calcular_hash(settings.HASH_INTEGRIDAD_SAL)

            # RN-05: generar URL del QR publico
            lote.codigo_qr = generar_url_qr(lote.codigo_lote, settings.URL_BASE_SISTEMA)

            tipo_evento = "aprobacion"
            desc        = (
                f"Lote clasificado como '{categoria}' ({datos.numero_defectos} defectos). "
                "Hash de integridad generado. QR publico activado."
            )
        else:
            lote.estado = "con_problema"
            tipo_evento = "problema_detectado"
            desc        = (
                f"Lote clasificado como '{categoria}' ({datos.numero_defectos} defectos). "
                "Requiere revision o reclasificacion."
            )

        self._registrar_evento(
            lote, tipo_evento, desc, usuario_id,
            anterior, lote.estado,
            datos_adicionales={
                "categoria": categoria,
                "defectos": datos.numero_defectos,
                "humedad": datos.humedad_pct,
                "aprobado": aprobado,
            },
        )

        self.db.commit()
        self.db.refresh(clasificacion)

        return ClasificacionResponse(
            id_clasificacion      = clasificacion.id_clasificacion,
            categoria             = categoria,
            categoria_legible     = DESCRIPCIONES_CATEGORIA[categoria],
            numero_defectos       = datos.numero_defectos,
            humedad_pct           = datos.humedad_pct,
            puntaje_taza          = datos.puntaje_taza,
            precio_sugerido_kg    = float(precio) if precio else None,
            aprobado_exportacion  = aprobado,
            metodo                = datos.metodo,
            confianza_ia          = confianza,
            descripcion_categoria = DESCRIPCIONES_CATEGORIA[categoria],
            recomendacion         = self._recomendacion_clasificacion(categoria, aprobado, datos),
            estado_lote_nuevo     = lote.estado,
            id_lote               = id_lote,
            fecha_clasificacion   = clasificacion.fecha_clasificacion,
        )

    # ----------------------------------------------------------
    # RF-15 / RN-05 — CONSULTA PUBLICA POR QR
    # ----------------------------------------------------------

    def consulta_publica(self, codigo_lote: str) -> LotePublicoResponse:
        """
        RF-15 + RN-05: endpoint publico consultado por el consumidor
        mediante escaneo del QR. No requiere autenticacion.
        Solo expone datos de trazabilidad y calidad, nunca datos
        internos como IDs, usuarios, precios de compra o documentos.
        """
        lote = (
            self.db.query(TrazabilidadLote)
            .filter(TrazabilidadLote.codigo_lote == codigo_lote)
            .first()
        )
        if not lote:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No se encontro el lote '{codigo_lote}'.",
            )

        if lote.estado not in ("aprobado", "vendido"):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Este lote no esta disponible para consulta publica aun.",
            )

        # Obtener informacion del cultivo para la region
        region = None
        try:
            r = self.db.execute(
                text("SELECT municipio FROM tbl_cultivo WHERE id_cultivo = :c"),
                {"c": lote.id_cultivo},
            ).fetchone()
            if r:
                region = r.municipio
        except Exception:
            pass

        return LotePublicoResponse(
            codigo_lote           = lote.codigo_lote,
            variedad_cafe         = lote.variedad_cafe.replace("_", " ").title(),
            fecha_cosecha         = lote.fecha_cosecha.strftime("%B %Y"),
            region_origen         = region,
            metodo_cosecha        = lote.metodo_cosecha.replace("_", " ").title(),
            metodo_beneficio      = (lote.metodo_beneficio or "").replace("_", " ").title() or None,
            clasificacion_calidad = lote.clasificacion_calidad.replace("_", " ").title(),
            puntaje_taza          = lote.puntaje_taza,
            aprobado_exportacion  = lote.clasificacion_calidad in ("supremo", "excelso_extra", "excelso"),
            destino_exportacion   = lote.destino_exportacion,
            mensaje_calidad       = MENSAJES_CALIDAD_PUBLICA.get(
                lote.clasificacion_calidad, MENSAJES_CALIDAD_PUBLICA["sin_clasificar"]
            ),
        )

    def log_eventos(self, id_lote: int, usuario_id: int) -> List[EventoResponse]:
        """Retorna el log cronologico de eventos del lote."""
        self._verificar_acceso_lote(id_lote, usuario_id)
        eventos = (
            self.db.query(EventoTrazabilidad)
            .filter(EventoTrazabilidad.id_lote == id_lote)
            .order_by(EventoTrazabilidad.fecha_evento.asc())
            .all()
        )
        return [
            EventoResponse(
                id_evento       = e.id_evento,
                tipo_evento     = e.tipo_evento,
                estado_anterior = e.estado_anterior,
                estado_nuevo    = e.estado_nuevo,
                descripcion     = e.descripcion,
                id_lote         = e.id_lote,
                id_usuario      = e.id_usuario,
                fecha_evento    = e.fecha_evento,
            )
            for e in eventos
        ]

    # ----------------------------------------------------------
    # HELPERS INTERNOS
    # ----------------------------------------------------------

    def _alerta_temperatura_secado(self, temp: float) -> Optional[str]:
        if temp > settings.SECADO_TEMP_CRITICA:
            return (
                f"CRITICO: Temperatura {temp}C supera {settings.SECADO_TEMP_CRITICA}C. "
                "Riesgo de daño termico al grano. Reduzca inmediatamente."
            )
        if temp > settings.SECADO_TEMP_MAX_OPTIMA:
            return (
                f"Temperatura {temp}C por encima del optimo ({settings.SECADO_TEMP_MAX_OPTIMA}C). "
                "Reduzca la exposicion solar o la temperatura del secador."
            )
        if temp < settings.SECADO_TEMP_MIN_OPTIMA:
            return (
                f"Temperatura {temp}C por debajo del optimo ({settings.SECADO_TEMP_MIN_OPTIMA}C). "
                "El secado sera mas lento. Considere usar secador mecanico."
            )
        return None

    def _alerta_humedad_secado(self, hum: Optional[float]) -> Optional[str]:
        if hum is None:
            return None
        if hum > 40.0:
            return (
                f"Humedad del grano muy alta ({hum}%). "
                "El proceso de secado esta en etapa inicial. Continue el monitoreo cada 6h."
            )
        if hum <= settings.SECADO_HUMEDAD_OBJETIVO:
            return None
        if hum <= 13.0:
            return (
                f"Humedad {hum}% cerca del objetivo ({settings.SECADO_HUMEDAD_OBJETIVO}%). "
                "El proceso se completara pronto. Monitoree cada 2h."
            )
        return None

    def _recomendacion_clasificacion(
        self, categoria: str, aprobado: bool, datos: ClasificacionCreate
    ) -> str:
        if aprobado:
            reco = (
                f"Lote clasificado como {DESCRIPCIONES_CATEGORIA[categoria]}. "
                "Trazabilidad completa activada. El QR publico ya esta disponible para el consumidor. "
                "Puede proceder al registro de la venta."
            )
        else:
            reco = (
                f"Lote clasificado como {DESCRIPCIONES_CATEGORIA[categoria]}. "
                "Revise los factores de calidad: "
            )
            if datos.numero_defectos > settings.DEFECTOS_MAX_EXCELSO:
                reco += f"defectos ({datos.numero_defectos}) superan el maximo para exportacion. "
            if datos.humedad_pct > settings.HUMEDAD_MAX_EXPORTACION:
                reco += f"humedad ({datos.humedad_pct}%) supera el maximo ({settings.HUMEDAD_MAX_EXPORTACION}%). "
            reco += "Puede reclasificar el lote luego de tomar acciones correctivas."
        return reco

    def _lote_a_response(self, lote: TrazabilidadLote) -> LoteResponse:
        return LoteResponse(
            id_lote               = lote.id_lote,
            codigo_lote           = lote.codigo_lote,
            variedad_cafe         = lote.variedad_cafe,
            fecha_cosecha         = lote.fecha_cosecha,
            metodo_cosecha        = lote.metodo_cosecha,
            kg_cereza_cosechados  = float(lote.kg_cereza_cosechados),
            metodo_beneficio      = lote.metodo_beneficio,
            kg_pergamino_seco     = float(lote.kg_pergamino_seco)  if lote.kg_pergamino_seco  else None,
            humedad_final_pct     = lote.humedad_final_pct,
            clasificacion_calidad = lote.clasificacion_calidad,
            puntaje_taza          = lote.puntaje_taza,
            numero_defectos       = lote.numero_defectos,
            precio_venta_kg       = float(lote.precio_venta_kg)    if lote.precio_venta_kg    else None,
            comprador             = lote.comprador,
            fecha_venta           = lote.fecha_venta,
            destino_exportacion   = lote.destino_exportacion,
            estado                = lote.estado,
            validado              = lote.validado,
            codigo_qr             = lote.codigo_qr,
            hash_integridad       = lote.hash_integridad,
            observaciones         = lote.observaciones,
            id_cultivo            = lote.id_cultivo,
            fecha_creacion        = lote.fecha_creacion,
            fecha_actualizacion   = lote.fecha_actualizacion,
        )
