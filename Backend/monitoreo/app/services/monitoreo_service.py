# ==============================================================
# modulo_03_monitoreo / app/services/monitoreo_service.py
# Logica de negocio - Monitoreo Ambiental y de Suelo
#
# Responsabilidades principales:
#   1. Registrar lecturas ambientales (RF-03) y de suelo (RF-04)
#   2. Calcular alertas agronomicas en tiempo real
#   3. Interpretar el estado del suelo para el caficultor
#   4. Validar la frescura de los datos para RN-03
#      (consultado por el Modulo 04 antes de recomendar)
#   5. Generar el resumen del panel del Caficultor
# ==============================================================

import logging
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.monitoreo import MonitoreoAmbiental, MonitoreoSuelo
from app.schemas.monitoreo import (
    MonitoreoAmbientalCreate, MonitoreoAmbientalResponse,
    MonitoreoSueloCreate, MonitoreoSueloResponse,
    ValidezDatosResponse, ResumenMonitoreoResponse,
)

logger = logging.getLogger(__name__)


# ==============================================================
# RANGOS AGRONOMICOS PARA CAFE EN COLOMBIA
# Fuente: CENICAFE - Centro Nacional de Investigaciones de Cafe
# ==============================================================

RANGOS_AMBIENTAL = {
    "temperatura_min_optima":  18.0,
    "temperatura_max_optima":  24.0,
    "temperatura_alerta_baja": 14.0,
    "temperatura_alerta_alta": 30.0,
    "humedad_min_optima":      70.0,
    "humedad_max_optima":      90.0,
    "humedad_alerta_baja":     55.0,
    "humedad_alerta_alta":     95.0,
}

RANGOS_SUELO = {
    "ph_min_optimo":    5.5,
    "ph_max_optimo":    6.5,
    "ph_alerta_acido":  4.5,
    "ph_alerta_alcali": 7.5,
    "humedad_min":      40.0,
    "humedad_max":      80.0,
    "nitrogeno_min":    20.0,
    "fosforo_min":      15.0,
    "potasio_min":      20.0,
}


class MonitoreoService:
    """Servicio de monitoreo ambiental y de suelo."""

    def __init__(self, db: Session):
        self.db = db

    # ----------------------------------------------------------
    # VERIFICACION DE PROPIEDAD DEL CULTIVO
    # ----------------------------------------------------------

    def _verificar_acceso_cultivo(
        self, cultivo_id: int, usuario_id: int
    ) -> None:
        """
        Verifica que el cultivo pertenezca al usuario autenticado.
        Lanza HTTP 404 si no existe o no tiene acceso.
        """
        resultado = self.db.execute(
            text(
                "SELECT id_cultivo FROM tbl_cultivo "
                "WHERE id_cultivo = :cid AND id_usuario = :uid "
                "AND estado != 'eliminado'"
            ),
            {"cid": cultivo_id, "uid": usuario_id},
        ).fetchone()

        if not resultado:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=(
                    f"Cultivo {cultivo_id} no encontrado "
                    "o no tiene acceso a este recurso"
                ),
            )

    # ----------------------------------------------------------
    # RF-03 - MONITOREO AMBIENTAL
    # ----------------------------------------------------------

    def registrar_ambiental(
        self,
        cultivo_id: int,
        datos:      MonitoreoAmbientalCreate,
        usuario_id: int,
    ) -> MonitoreoAmbientalResponse:
        """
        RF-03: registra una lectura ambiental del cultivo.
        Verifica acceso, calcula alertas y persiste el registro.
        Acepta lecturas de sensores IoT, ingreso manual o API externa.
        """
        self._verificar_acceso_cultivo(cultivo_id, usuario_id)
        self._validar_al_menos_una_variable_ambiental(datos)

        registro = MonitoreoAmbiental(
            temperatura=datos.temperatura,
            humedad_relativa=datos.humedad_relativa,
            precipitacion_mm=datos.precipitacion_mm,
            radiacion_solar=datos.radiacion_solar,
            velocidad_viento=datos.velocidad_viento,
            origen_dato=datos.origen_dato,
            id_sensor=datos.id_sensor,
            observaciones=datos.observaciones,
            id_cultivo=cultivo_id,
        )
        self.db.add(registro)
        self.db.commit()
        self.db.refresh(registro)

        alerta_temp, alerta_hum = self._calcular_alertas_ambientales(datos)

        if alerta_temp or alerta_hum:
            logger.warning(
                f"Alerta ambiental cultivo={cultivo_id}: "
                f"temp='{alerta_temp}' hum='{alerta_hum}'"
            )

        logger.info(
            f"Monitoreo ambiental: cultivo={cultivo_id} "
            f"origen='{datos.origen_dato}' "
            f"temp={datos.temperatura} hum={datos.humedad_relativa}"
        )

        return MonitoreoAmbientalResponse(
            id_monitoreo=registro.id_monitoreo,
            temperatura=float(registro.temperatura) if registro.temperatura else None,
            humedad_relativa=float(registro.humedad_relativa) if registro.humedad_relativa else None,
            precipitacion_mm=float(registro.precipitacion_mm) if registro.precipitacion_mm else None,
            radiacion_solar=float(registro.radiacion_solar) if registro.radiacion_solar else None,
            velocidad_viento=float(registro.velocidad_viento) if registro.velocidad_viento else None,
            origen_dato=registro.origen_dato,
            id_sensor=registro.id_sensor,
            observaciones=registro.observaciones,
            fecha_registro=registro.fecha_registro,
            id_cultivo=registro.id_cultivo,
            alerta_temperatura=alerta_temp,
            alerta_humedad=alerta_hum,
        )

    def listar_ambiental(
        self,
        cultivo_id: int,
        usuario_id: int,
        limite:     int = 50,
    ) -> List[MonitoreoAmbientalResponse]:
        """
        RF-03: retorna el historial de lecturas ambientales.
        Ordenado de mas reciente a mas antiguo (limite: max 500).
        """
        self._verificar_acceso_cultivo(cultivo_id, usuario_id)
        limite = min(limite, 500)

        registros = (
            self.db.query(MonitoreoAmbiental)
            .filter(MonitoreoAmbiental.id_cultivo == cultivo_id)
            .order_by(MonitoreoAmbiental.fecha_registro.desc())
            .limit(limite)
            .all()
        )
        return [self._orm_ambiental_a_response(r) for r in registros]

    def ultima_lectura_ambiental(
        self, cultivo_id: int, usuario_id: int
    ) -> Optional[MonitoreoAmbientalResponse]:
        """Retorna la lectura ambiental mas reciente del cultivo."""
        self._verificar_acceso_cultivo(cultivo_id, usuario_id)
        registro = (
            self.db.query(MonitoreoAmbiental)
            .filter(MonitoreoAmbiental.id_cultivo == cultivo_id)
            .order_by(MonitoreoAmbiental.fecha_registro.desc())
            .first()
        )
        if not registro:
            return None
        return self._orm_ambiental_a_response(registro)

    # ----------------------------------------------------------
    # RF-04 - MONITOREO DE SUELO
    # ----------------------------------------------------------

    def registrar_suelo(
        self,
        cultivo_id: int,
        datos:      MonitoreoSueloCreate,
        usuario_id: int,
    ) -> MonitoreoSueloResponse:
        """
        RF-04: registra una lectura del estado del suelo.
        Verifica acceso, interpreta el pH, alerta sobre
        deficiencias de nutrientes y persiste el registro.
        """
        self._verificar_acceso_cultivo(cultivo_id, usuario_id)
        self._validar_al_menos_una_variable_suelo(datos)

        registro = MonitoreoSuelo(
            ph=datos.ph,
            humedad_suelo=datos.humedad_suelo,
            nitrogeno=datos.nitrogeno,
            fosforo=datos.fosforo,
            potasio=datos.potasio,
            materia_organica=datos.materia_organica,
            conductividad_ec=datos.conductividad_ec,
            origen_dato=datos.origen_dato,
            id_sensor=datos.id_sensor,
            observaciones=datos.observaciones,
            id_cultivo=cultivo_id,
        )
        self.db.add(registro)
        self.db.commit()
        self.db.refresh(registro)

        interp_ph       = self._interpretar_ph(datos.ph)
        alerta_nutrient = self._calcular_alerta_nutrientes(datos)

        logger.info(
            f"Monitoreo suelo: cultivo={cultivo_id} "
            f"origen='{datos.origen_dato}' "
            f"pH={datos.ph} hum={datos.humedad_suelo}"
        )

        return MonitoreoSueloResponse(
            id_monitoreo_suelo=registro.id_monitoreo_suelo,
            ph=float(registro.ph) if registro.ph else None,
            humedad_suelo=float(registro.humedad_suelo) if registro.humedad_suelo else None,
            nitrogeno=float(registro.nitrogeno) if registro.nitrogeno else None,
            fosforo=float(registro.fosforo) if registro.fosforo else None,
            potasio=float(registro.potasio) if registro.potasio else None,
            materia_organica=float(registro.materia_organica) if registro.materia_organica else None,
            conductividad_ec=float(registro.conductividad_ec) if registro.conductividad_ec else None,
            origen_dato=registro.origen_dato,
            id_sensor=registro.id_sensor,
            observaciones=registro.observaciones,
            fecha_registro=registro.fecha_registro,
            id_cultivo=registro.id_cultivo,
            interpretacion_ph=interp_ph,
            alerta_nutrientes=alerta_nutrient,
        )

    def listar_suelo(
        self,
        cultivo_id: int,
        usuario_id: int,
        limite:     int = 50,
    ) -> List[MonitoreoSueloResponse]:
        """RF-04: retorna el historial de lecturas de suelo."""
        self._verificar_acceso_cultivo(cultivo_id, usuario_id)
        limite = min(limite, 500)

        registros = (
            self.db.query(MonitoreoSuelo)
            .filter(MonitoreoSuelo.id_cultivo == cultivo_id)
            .order_by(MonitoreoSuelo.fecha_registro.desc())
            .limit(limite)
            .all()
        )
        return [self._orm_suelo_a_response(r) for r in registros]

    def ultima_lectura_suelo(
        self, cultivo_id: int, usuario_id: int
    ) -> Optional[MonitoreoSueloResponse]:
        """Retorna la lectura de suelo mas reciente del cultivo."""
        self._verificar_acceso_cultivo(cultivo_id, usuario_id)
        registro = (
            self.db.query(MonitoreoSuelo)
            .filter(MonitoreoSuelo.id_cultivo == cultivo_id)
            .order_by(MonitoreoSuelo.fecha_registro.desc())
            .first()
        )
        if not registro:
            return None
        return self._orm_suelo_a_response(registro)

    # ----------------------------------------------------------
    # RN-03 - VALIDACION DE DATOS ACTUALIZADOS
    # ----------------------------------------------------------

    def verificar_validez_rn03(
        self, cultivo_id: int, usuario_id: int
    ) -> ValidezDatosResponse:
        """
        RN-03: verifica si los datos ambientales y de suelo
        estan actualizados segun el umbral configurado
        (HORAS_DATOS_VALIDOS, por defecto 24 horas).

        Este metodo es consumido directamente por el Modulo 04
        de IA antes de generar cualquier recomendacion automatica.
        Si ambos_validos=False el modulo de IA debe rechazar
        la recomendacion con un mensaje claro al usuario.
        """
        self._verificar_acceso_cultivo(cultivo_id, usuario_id)

        ahora  = datetime.now(timezone.utc)  # L-02 FIX: 'limite' no se usaba

        # Ultima lectura ambiental
        ult_amb = (
            self.db.query(MonitoreoAmbiental)
            .filter(MonitoreoAmbiental.id_cultivo == cultivo_id)
            .order_by(MonitoreoAmbiental.fecha_registro.desc())
            .first()
        )

        # Ultima lectura de suelo
        ult_sue = (
            self.db.query(MonitoreoSuelo)
            .filter(MonitoreoSuelo.id_cultivo == cultivo_id)
            .order_by(MonitoreoSuelo.fecha_registro.desc())
            .first()
        )

        # Calcular validez ambiental
        fecha_amb       = None
        horas_amb       = None
        ambiental_val   = False
        if ult_amb:
            fecha_amb = ult_amb.fecha_registro
            if fecha_amb.tzinfo is None:
                fecha_amb = fecha_amb.replace(tzinfo=timezone.utc)
            horas_amb = (ahora - fecha_amb).total_seconds() / 3600
            ambiental_val = horas_amb <= settings.HORAS_DATOS_VALIDOS

        # Calcular validez de suelo
        fecha_sue       = None
        horas_sue       = None
        suelo_val       = False
        if ult_sue:
            fecha_sue = ult_sue.fecha_registro
            if fecha_sue.tzinfo is None:
                fecha_sue = fecha_sue.replace(tzinfo=timezone.utc)
            horas_sue = (ahora - fecha_sue).total_seconds() / 3600
            suelo_val = horas_sue <= settings.HORAS_DATOS_VALIDOS

        ambos = ambiental_val and suelo_val

        # Mensaje descriptivo para el usuario
        if ambos:
            mensaje = (
                "Los datos ambientales y de suelo estan actualizados. "
                "El sistema puede generar recomendaciones automaticas."
            )
        elif not ambiental_val and not suelo_val:
            mensaje = (
                f"Los datos ambientales y de suelo superaron el limite "
                f"de {settings.HORAS_DATOS_VALIDOS} horas. "
                "Registre nuevas lecturas para habilitar las recomendaciones de IA."
            )
        elif not ambiental_val:
            mensaje = (
                f"Los datos ambientales superaron el limite de "
                f"{settings.HORAS_DATOS_VALIDOS} horas. "
                "Registre una lectura ambiental actualizada."
            )
        else:
            mensaje = (
                f"Los datos de suelo superaron el limite de "
                f"{settings.HORAS_DATOS_VALIDOS} horas. "
                "Registre una lectura de suelo actualizada."
            )

        return ValidezDatosResponse(
            cultivo_id=cultivo_id,
            ambiental_valido=ambiental_val,
            suelo_valido=suelo_val,
            ambos_validos=ambos,
            horas_limite=settings.HORAS_DATOS_VALIDOS,
            ultima_lectura_ambiental=fecha_amb,
            ultima_lectura_suelo=fecha_sue,
            horas_desde_ambiental=round(horas_amb, 2) if horas_amb else None,
            horas_desde_suelo=round(horas_sue, 2) if horas_sue else None,
            mensaje=mensaje,
        )

    # ----------------------------------------------------------
    # RESUMEN DEL DASHBOARD
    # ----------------------------------------------------------

    def resumen_monitoreo(
        self, cultivo_id: int, usuario_id: int
    ) -> ResumenMonitoreoResponse:
        """
        Genera el resumen de monitoreo para el panel del Caficultor.
        Consolida ultima lectura ambiental, ultima lectura de suelo,
        estado de validez RN-03 y alertas activas en una sola respuesta.
        """
        validez = self.verificar_validez_rn03(cultivo_id, usuario_id)
        alertas = []

        # Ultima ambiental
        ult_amb = (
            self.db.query(MonitoreoAmbiental)
            .filter(MonitoreoAmbiental.id_cultivo == cultivo_id)
            .order_by(MonitoreoAmbiental.fecha_registro.desc())
            .first()
        )

        # Ultima suelo
        ult_sue = (
            self.db.query(MonitoreoSuelo)
            .filter(MonitoreoSuelo.id_cultivo == cultivo_id)
            .order_by(MonitoreoSuelo.fecha_registro.desc())
            .first()
        )

        # Calcular alertas activas
        if ult_amb:
            temp = float(ult_amb.temperatura) if ult_amb.temperatura else None
            hum  = float(ult_amb.humedad_relativa) if ult_amb.humedad_relativa else None
            if temp:
                if temp < RANGOS_AMBIENTAL["temperatura_alerta_baja"]:
                    alertas.append(f"Temperatura muy baja: {temp}C (minimo recomendado 14C)")
                elif temp > RANGOS_AMBIENTAL["temperatura_alerta_alta"]:
                    alertas.append(f"Temperatura muy alta: {temp}C (maximo recomendado 30C)")
            if hum:
                if hum < RANGOS_AMBIENTAL["humedad_alerta_baja"]:
                    alertas.append(f"Humedad muy baja: {hum}% (minimo recomendado 55%)")

        if ult_sue:
            ph = float(ult_sue.ph) if ult_sue.ph else None
            n  = float(ult_sue.nitrogeno) if ult_sue.nitrogeno else None
            p  = float(ult_sue.fosforo) if ult_sue.fosforo else None
            k  = float(ult_sue.potasio) if ult_sue.potasio else None
            if ph:
                if ph < RANGOS_SUELO["ph_alerta_acido"]:
                    alertas.append(f"pH muy acido: {ph} (minimo critico 4.5)")
                elif ph > RANGOS_SUELO["ph_alerta_alcali"]:
                    alertas.append(f"pH muy alcalino: {ph} (maximo critico 7.5)")
            if n and n < RANGOS_SUELO["nitrogeno_min"]:
                alertas.append(f"Deficiencia de Nitrogeno: {n} mg/kg (minimo 20 mg/kg)")
            if p and p < RANGOS_SUELO["fosforo_min"]:
                alertas.append(f"Deficiencia de Fosforo: {p} mg/kg (minimo 15 mg/kg)")
            if k and k < RANGOS_SUELO["potasio_min"]:
                alertas.append(f"Deficiencia de Potasio: {k} mg/kg (minimo 20 mg/kg)")

        if not validez.ambos_validos:
            alertas.append(
                "Datos desactualizados: registre lecturas nuevas para "
                "habilitar recomendaciones de IA (RN-03)"  # L-03 FIX
            )

        return ResumenMonitoreoResponse(
            cultivo_id=cultivo_id,
            ultima_temperatura=float(ult_amb.temperatura) if ult_amb and ult_amb.temperatura else None,
            ultima_humedad_rel=float(ult_amb.humedad_relativa) if ult_amb and ult_amb.humedad_relativa else None,
            ultima_precipitacion=float(ult_amb.precipitacion_mm) if ult_amb and ult_amb.precipitacion_mm else None,
            ultimo_ph=float(ult_sue.ph) if ult_sue and ult_sue.ph else None,
            ultima_humedad_suelo=float(ult_sue.humedad_suelo) if ult_sue and ult_sue.humedad_suelo else None,
            ultimo_nitrogeno=float(ult_sue.nitrogeno) if ult_sue and ult_sue.nitrogeno else None,
            datos_validos_rn03=validez.ambos_validos,
            alertas=alertas,
            fecha_ultima_ambiental=validez.ultima_lectura_ambiental,
            fecha_ultima_suelo=validez.ultima_lectura_suelo,
        )

    # ----------------------------------------------------------
    # LOGICA DE ALERTAS Y CLASIFICACION AGRONOMICA
    # ----------------------------------------------------------

    def _calcular_alertas_ambientales(
        self, datos: MonitoreoAmbientalCreate
    ) -> Tuple[Optional[str], Optional[str]]:
        """Calcula alertas de temperatura y humedad relativa."""
        alerta_temp = None
        alerta_hum  = None

        if datos.temperatura is not None:
            t = datos.temperatura
            if t < RANGOS_AMBIENTAL["temperatura_alerta_baja"]:
                alerta_temp = (
                    f"Temperatura critica baja ({t}C). "
                    "Riesgo de daño por frio en flores y frutos."
                )
            elif t > RANGOS_AMBIENTAL["temperatura_alerta_alta"]:
                alerta_temp = (
                    f"Temperatura critica alta ({t}C). "
                    "Riesgo de estres hidrico y quemadura foliar."
                )
            elif t < RANGOS_AMBIENTAL["temperatura_min_optima"]:
                alerta_temp = (
                    f"Temperatura por debajo del optimo ({t}C). "
                    "Rango optimo para cafe: 18-24 C."
                )
            elif t > RANGOS_AMBIENTAL["temperatura_max_optima"]:
                alerta_temp = (
                    f"Temperatura por encima del optimo ({t}C). "
                    "Rango optimo para cafe: 18-24 C."
                )

        if datos.humedad_relativa is not None:
            h = datos.humedad_relativa
            if h < RANGOS_AMBIENTAL["humedad_alerta_baja"]:
                alerta_hum = (
                    f"Humedad muy baja ({h}%). "
                    "Riesgo de estres hidrico. Considere riego inmediato."
                )
            elif h > RANGOS_AMBIENTAL["humedad_alerta_alta"]:
                alerta_hum = (
                    f"Humedad muy alta ({h}%). "
                    "Condiciones favorables para Roya y enfermedades fungicas."
                )

        return alerta_temp, alerta_hum

    def _interpretar_ph(self, ph: Optional[float]) -> Optional[str]:
        """Retorna una interpretacion agronomica del pH del suelo."""
        if ph is None:
            return None
        if ph < RANGOS_SUELO["ph_alerta_acido"]:
            return (
                f"pH muy acido ({ph}). Requiere encalado urgente. "
                "Aplique cal dolomitica para subir el pH."
            )
        elif ph < RANGOS_SUELO["ph_min_optimo"]:
            return (
                f"pH ligeramente acido ({ph}). "
                "Considere encalado moderado. Rango optimo: 5.5-6.5."
            )
        elif ph <= RANGOS_SUELO["ph_max_optimo"]:
            return (
                f"pH optimo para cafe ({ph}). "
                "Condiciones ideales para absorcion de nutrientes."
            )
        elif ph <= RANGOS_SUELO["ph_alerta_alcali"]:
            return (
                f"pH ligeramente alcalino ({ph}). "
                "Puede dificultar absorcion de hierro y manganeso."
            )
        else:
            return (
                f"pH muy alcalino ({ph}). "
                "Aplique azufre agricola para reducir el pH."
            )

    def _calcular_alerta_nutrientes(
        self, datos: MonitoreoSueloCreate
    ) -> Optional[str]:
        """Detecta deficiencias en macronutrientes NPK."""
        deficiencias = []
        if datos.nitrogeno is not None and datos.nitrogeno < RANGOS_SUELO["nitrogeno_min"]:
            deficiencias.append(f"N ({datos.nitrogeno} mg/kg)")
        if datos.fosforo is not None and datos.fosforo < RANGOS_SUELO["fosforo_min"]:
            deficiencias.append(f"P ({datos.fosforo} mg/kg)")
        if datos.potasio is not None and datos.potasio < RANGOS_SUELO["potasio_min"]:
            deficiencias.append(f"K ({datos.potasio} mg/kg)")

        if not deficiencias:
            return None
        return (
            "Deficiencia detectada en: " + ", ".join(deficiencias) + ". "
            "Consulte el modulo de IA para recomendacion de fertilizacion."
        )

    def _validar_al_menos_una_variable_ambiental(
        self, datos: MonitoreoAmbientalCreate
    ) -> None:
        variables = [
            datos.temperatura, datos.humedad_relativa,
            datos.precipitacion_mm, datos.radiacion_solar,
            datos.velocidad_viento,
        ]
        if all(v is None for v in variables):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "Debe ingresar al menos una variable ambiental: "
                    "temperatura, humedad_relativa, precipitacion_mm, "
                    "radiacion_solar o velocidad_viento."
                ),
            )

    def _validar_al_menos_una_variable_suelo(
        self, datos: MonitoreoSueloCreate
    ) -> None:
        variables = [
            datos.ph, datos.humedad_suelo, datos.nitrogeno,
            datos.fosforo, datos.potasio, datos.materia_organica,
            datos.conductividad_ec,
        ]
        if all(v is None for v in variables):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "Debe ingresar al menos una variable de suelo: "
                    "ph, humedad_suelo, nitrogeno, fosforo, potasio, "
                    "materia_organica o conductividad_ec."
                ),
            )

    # ----------------------------------------------------------
    # CONVERSORES ORM -> RESPONSE
    # ----------------------------------------------------------

    def _orm_ambiental_a_response(
        self, r: MonitoreoAmbiental
    ) -> MonitoreoAmbientalResponse:
        return MonitoreoAmbientalResponse(
            id_monitoreo=r.id_monitoreo,
            temperatura=float(r.temperatura) if r.temperatura else None,
            humedad_relativa=float(r.humedad_relativa) if r.humedad_relativa else None,
            precipitacion_mm=float(r.precipitacion_mm) if r.precipitacion_mm else None,
            radiacion_solar=float(r.radiacion_solar) if r.radiacion_solar else None,
            velocidad_viento=float(r.velocidad_viento) if r.velocidad_viento else None,
            origen_dato=r.origen_dato,
            id_sensor=r.id_sensor,
            observaciones=r.observaciones,
            fecha_registro=r.fecha_registro,
            id_cultivo=r.id_cultivo,
        )

    def _orm_suelo_a_response(
        self, r: MonitoreoSuelo
    ) -> MonitoreoSueloResponse:
        return MonitoreoSueloResponse(
            id_monitoreo_suelo=r.id_monitoreo_suelo,
            ph=float(r.ph) if r.ph else None,
            humedad_suelo=float(r.humedad_suelo) if r.humedad_suelo else None,
            nitrogeno=float(r.nitrogeno) if r.nitrogeno else None,
            fosforo=float(r.fosforo) if r.fosforo else None,
            potasio=float(r.potasio) if r.potasio else None,
            materia_organica=float(r.materia_organica) if r.materia_organica else None,
            conductividad_ec=float(r.conductividad_ec) if r.conductividad_ec else None,
            origen_dato=r.origen_dato,
            id_sensor=r.id_sensor,
            observaciones=r.observaciones,
            fecha_registro=r.fecha_registro,
            id_cultivo=r.id_cultivo,
        )
