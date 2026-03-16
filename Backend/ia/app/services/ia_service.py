# ==============================================================
# modulo_04_ia / app/services/ia_service.py
# Servicio orquestador de todos los modelos de IA
#
# Implementa el flujo completo del Diagrama de Secuencia oficial:
#   1  seleccionarImagen
#   2  cargarImagen
#   3  enviarImagen
#   4  procesarImagen (validaciones)
#   5  enviarAIA      (llamar motor)
#   6  analizarImagen (inferencia)
#   7  generarDiagnostico
#   8  retornarResultado (construir respuesta)
#   9  guardarResultado  (persistir en BD)
#   10 mostrarResultados (retornar al controlador)
#
# RN-03: antes de RF-07, RF-08 y RF-09 verifica que los datos
# del M03 sean frescos consultando tbl_monitoreo_ambiental
# y tbl_monitoreo_suelo directamente en BD (sin HTTP entre
# servicios, para mayor resiliencia en zonas rurales).
# ==============================================================

import json
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Optional

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.ia.motor.clasificador_imagen import (
    ClasificadorImagen, obtener_recomendacion,
)
from app.ia.motor.predictor_fitosanitario import (
    predecir_riesgo, generar_recomendacion_fito,
)
from app.ia.motor.recomendador_riego import recomendar_riego
from app.ia.motor.recomendador_fertilizacion import recomendar_fertilizacion
from app.models.analisis import (
    AnalisisImagen, PrediccionFitosanitaria,
    RecomendacionRiego, RecomendacionFertilizacion,
)
from app.schemas.analisis import (
    AnalisisImagenResponse, HistorialAnalisisResponse,
    PrediccionFitoResponse, RecomendacionRiegoResponse,
    RecomendacionFertResponse, ResumenIAResponse,
    ClaseConfianza,
)

logger = logging.getLogger(__name__)

# Tipos de imagen permitidos (RNF-01)
TIPOS_PERMITIDOS = set(settings.IMAGEN_TIPOS_PERMITIDOS.split(","))


class IAService:
    """
    Servicio principal del Modulo 04.
    Orquesta los cuatro motores de IA y gestiona la persistencia
    de todos los resultados en la base de datos.
    """

    def __init__(self, db: Session):
        self.db = db

    # ----------------------------------------------------------
    # UTILIDADES INTERNAS
    # ----------------------------------------------------------

    def _verificar_acceso_cultivo(self, cultivo_id: int, usuario_id: int) -> None:
        r = self.db.execute(
            text(
                "SELECT id_cultivo FROM tbl_cultivo "
                "WHERE id_cultivo = :c AND id_usuario = :u "
                "AND estado != 'eliminado'"
            ),
            {"c": cultivo_id, "u": usuario_id},
        ).fetchone()
        if not r:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Cultivo {cultivo_id} no encontrado o sin acceso.",
            )

    def _obtener_ultima_ambiental(self, cultivo_id: int) -> Optional[dict]:
        """Consulta la ultima lectura ambiental directamente en BD."""
        r = self.db.execute(
            text(
                "SELECT temperatura, humedad_relativa, precipitacion_mm, "
                "fecha_registro "
                "FROM tbl_monitoreo_ambiental "
                "WHERE id_cultivo = :c "
                "ORDER BY fecha_registro DESC LIMIT 1"
            ),
            {"c": cultivo_id},
        ).fetchone()
        return dict(r._mapping) if r else None

    def _obtener_ultima_suelo(self, cultivo_id: int) -> Optional[dict]:
        """Consulta la ultima lectura de suelo directamente en BD."""
        r = self.db.execute(
            text(
                "SELECT ph, humedad_suelo, nitrogeno, fosforo, potasio, "
                "materia_organica, fecha_registro "
                "FROM tbl_monitoreo_suelo "
                "WHERE id_cultivo = :c "
                "ORDER BY fecha_registro DESC LIMIT 1"
            ),
            {"c": cultivo_id},
        ).fetchone()
        return dict(r._mapping) if r else None

    def _verificar_rn03(
        self,
        cultivo_id:       int,
        requiere_ambiental: bool = True,
        requiere_suelo:     bool = True,
    ) -> tuple:
        """
        RN-03: verifica que los datos del M03 sean validos (< 24h).
        Lanza HTTP 422 con mensaje claro si los datos estan caducados.
        Retorna (datos_ambiental, datos_suelo).
        """
        limite    = timedelta(hours=settings.HORAS_DATOS_VALIDOS)
        ahora     = datetime.now(timezone.utc)
        amb       = None
        sue       = None

        if requiere_ambiental:
            amb = self._obtener_ultima_ambiental(cultivo_id)
            if not amb:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=(
                        "RN-03: No existen datos ambientales registrados para este cultivo. "
                        "Registre al menos una lectura en el Modulo de Monitoreo antes "
                        "de solicitar recomendaciones de IA."
                    ),
                )
            fecha = amb["fecha_registro"]
            if fecha.tzinfo is None:
                fecha = fecha.replace(tzinfo=timezone.utc)
            horas = (ahora - fecha).total_seconds() / 3600
            if horas > settings.HORAS_DATOS_VALIDOS:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=(
                        f"RN-03: Los datos ambientales tienen {horas:.1f} horas de antiguedad "
                        f"(maximo permitido: {settings.HORAS_DATOS_VALIDOS}h). "
                        "Registre una nueva lectura ambiental para habilitar la IA."
                    ),
                )

        if requiere_suelo:
            sue = self._obtener_ultima_suelo(cultivo_id)
            if not sue:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=(
                        "RN-03: No existen datos de suelo registrados para este cultivo. "
                        "Registre al menos una lectura de suelo en el Modulo de Monitoreo."
                    ),
                )
            fecha = sue["fecha_registro"]
            if fecha.tzinfo is None:
                fecha = fecha.replace(tzinfo=timezone.utc)
            horas = (ahora - fecha).total_seconds() / 3600
            if horas > settings.HORAS_DATOS_VALIDOS:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=(
                        f"RN-03: Los datos de suelo tienen {horas:.1f} horas de antiguedad "
                        f"(maximo permitido: {settings.HORAS_DATOS_VALIDOS}h). "
                        "Registre una nueva lectura de suelo para habilitar la IA."
                    ),
                )

        return amb, sue

    # ----------------------------------------------------------
    # RF-05 y RF-06 - ANALISIS DE IMAGEN
    # ----------------------------------------------------------

    async def analizar_imagen(
        self,
        cultivo_id:  int,
        usuario_id:  int,
        tipo:        str,         # 'enfermedad' | 'plaga'
        imagen:      UploadFile,
    ) -> AnalisisImagenResponse:
        """
        Flujo completo segun Diagrama de Secuencia (pasos 3-10):
          Paso 3  enviarImagen    - recibir archivo
          Paso 4  procesarImagen  - validar formato y tamano
          Paso 5  enviarAIA       - llamar al clasificador
          Paso 6  analizarImagen  - inferencia CNN
          Paso 7  generarDiag     - construir diagnostico
          Paso 8  retornarResult  - montar respuesta
          Paso 9  guardarResult   - persistir en BD
          Paso 10 mostrarResult   - retornar al controlador
        """
        self._verificar_acceso_cultivo(cultivo_id, usuario_id)

        # ---- Paso 4: validar imagen ----
        content_type = imagen.content_type or ""
        if content_type not in TIPOS_PERMITIDOS:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=(
                    f"Tipo de archivo '{content_type}' no permitido. "
                    f"Use: {', '.join(TIPOS_PERMITIDOS)}"
                ),
            )

        imagen_bytes = await imagen.read()
        tamano_kb    = len(imagen_bytes) // 1024

        if len(imagen_bytes) > settings.IMAGEN_MAX_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=(
                    f"Imagen demasiado grande ({tamano_kb} KB). "
                    f"Maximo permitido: {settings.IMAGEN_MAX_BYTES // 1024} KB."
                ),
            )

        if len(imagen_bytes) < 1000:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="La imagen parece estar vacia o corrupta (< 1 KB).",
            )

        # ---- Pasos 5-7: inferencia ----
        try:
            clasificador = ClasificadorImagen(tipo)
            diagnostico, confianza, top_raw, tiempo = clasificador.analizar(
                imagen_bytes, imagen.filename or ""
            )
        except TimeoutError as e:
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail=str(e),
            )

        # Verificar umbral de confianza
        if confianza < settings.UMBRAL_CONFIANZA_MINIMA:
            diagnostico = "sano"
            confianza   = confianza
            logger.warning(
                f"Confianza {confianza:.3f} por debajo del umbral "
                f"{settings.UMBRAL_CONFIANZA_MINIMA}. Reportando como 'sano'."
            )

        recomendacion, urgencia = obtener_recomendacion(tipo, diagnostico)

        # ---- Paso 9: guardar en BD ----
        registro = AnalisisImagen(
            tipo_analisis     = tipo,
            diagnostico       = diagnostico,
            confianza         = confianza,
            top_clases        = json.dumps(top_raw, ensure_ascii=False),
            recomendacion     = recomendacion,
            nivel_urgencia    = urgencia,
            version_modelo    = clasificador.version,
            tiempo_inferencia = tiempo,
            nombre_imagen     = imagen.filename,
            tamano_imagen_kb  = tamano_kb,
            id_cultivo        = cultivo_id,
            id_usuario        = usuario_id,
        )
        self.db.add(registro)

        # Actualizar estado del cultivo si se detecta un problema (Diagrama Estados)
        if diagnostico != "sano" and urgencia in ("alto", "critico"):
            self.db.execute(
                text(
                    "UPDATE tbl_cultivo SET estado = 'con_problema_detectado' "
                    "WHERE id_cultivo = :c AND estado = 'en_seguimiento'"
                ),
                {"c": cultivo_id},
            )

        self.db.commit()
        self.db.refresh(registro)

        # ---- Paso 10: construir respuesta ----
        top_clases = [
            ClaseConfianza(clase=t["clase"], probabilidad=t["probabilidad"])
            for t in top_raw
        ]

        return AnalisisImagenResponse(
            id_analisis       = registro.id_analisis,
            tipo_analisis     = tipo,
            diagnostico       = diagnostico,
            confianza         = round(confianza, 4),
            confianza_pct     = f"{confianza * 100:.1f}%",
            top_clases        = top_clases,
            recomendacion     = recomendacion,
            nivel_urgencia    = urgencia,
            version_modelo    = registro.version_modelo,
            tiempo_inferencia = round(tiempo, 3),
            tiempo_pct_rnf01  = f"{tiempo:.2f}s de {settings.TIMEOUT_INFERENCIA_SEG}s permitidos",
            nombre_imagen     = registro.nombre_imagen,
            fecha_analisis    = registro.fecha_analisis,
            id_cultivo        = cultivo_id,
        )

    def historial_analisis(
        self,
        cultivo_id: int,
        usuario_id: int,
        tipo:       Optional[str] = None,
        limite:     int = 20,
    ) -> List[HistorialAnalisisResponse]:
        """CP-07: historial de analisis del cultivo."""
        self._verificar_acceso_cultivo(cultivo_id, usuario_id)
        limite  = min(limite, 200)
        q = (
            self.db.query(AnalisisImagen)
            .filter(AnalisisImagen.id_cultivo == cultivo_id)
        )
        if tipo:
            q = q.filter(AnalisisImagen.tipo_analisis == tipo)
        registros = q.order_by(AnalisisImagen.fecha_analisis.desc()).limit(limite).all()
        return [
            HistorialAnalisisResponse(
                id_analisis    = r.id_analisis,
                tipo_analisis  = r.tipo_analisis,
                diagnostico    = r.diagnostico,
                confianza      = r.confianza,
                nivel_urgencia = r.nivel_urgencia,
                fecha_analisis = r.fecha_analisis,
                id_cultivo     = r.id_cultivo,
            )
            for r in registros
        ]

    # ----------------------------------------------------------
    # RF-07 - PREDICCION FITOSANITARIA
    # ----------------------------------------------------------

    def predecir_fitosanitario(
        self, cultivo_id: int, usuario_id: int
    ) -> PrediccionFitoResponse:
        """
        RF-07 + RN-03: predice riesgo fitosanitario usando datos
        ambientales actualizados del cultivo.
        """
        self._verificar_acceso_cultivo(cultivo_id, usuario_id)
        amb, _ = self._verificar_rn03(cultivo_id, requiere_ambiental=True, requiere_suelo=False)

        temp  = float(amb["temperatura"])      if amb.get("temperatura")      else None
        hum   = float(amb["humedad_relativa"]) if amb.get("humedad_relativa") else None
        prec  = float(amb["precipitacion_mm"]) if amb.get("precipitacion_mm") else None

        nivel, prob, factores, enf_prob = predecir_riesgo(temp, hum, prec)
        reco = generar_recomendacion_fito(nivel, factores)

        registro = PrediccionFitosanitaria(
            nivel_riesgo         = nivel,
            probabilidad_riesgo  = prob,
            factores_riesgo      = json.dumps(factores,   ensure_ascii=False),
            enfermedades_prob    = json.dumps(enf_prob,   ensure_ascii=False),
            recomendacion        = reco,
            temperatura_usada    = temp,
            humedad_usada        = hum,
            precipitacion_usada  = prec,
            version_modelo       = "reglas-cenicafe-1.0",
            id_cultivo           = cultivo_id,
            id_usuario           = usuario_id,
        )
        self.db.add(registro)
        self.db.commit()
        self.db.refresh(registro)

        return PrediccionFitoResponse(
            id_prediccion        = registro.id_prediccion,
            nivel_riesgo         = nivel,
            probabilidad_riesgo  = prob,
            probabilidad_pct     = f"{prob * 100:.1f}%",
            factores_riesgo      = factores,
            enfermedades_prob    = enf_prob,
            recomendacion        = reco,
            temperatura_usada    = temp,
            humedad_usada        = hum,
            precipitacion_usada  = prec,
            fecha_prediccion     = registro.fecha_prediccion,
            id_cultivo           = cultivo_id,
        )

    # ----------------------------------------------------------
    # RF-08 - RECOMENDACION DE RIEGO
    # ----------------------------------------------------------

    def recomendar_riego(
        self, cultivo_id: int, usuario_id: int
    ) -> RecomendacionRiegoResponse:
        """
        RF-08 + RN-03: genera recomendacion de riego usando
        datos de suelo y ambientales actualizados.
        """
        self._verificar_acceso_cultivo(cultivo_id, usuario_id)
        amb, sue = self._verificar_rn03(cultivo_id, True, True)

        hum_suelo = float(sue["humedad_suelo"]) if sue and sue.get("humedad_suelo") else None
        temp      = float(amb["temperatura"])    if amb and amb.get("temperatura")   else None
        prec      = float(amb["precipitacion_mm"]) if amb and amb.get("precipitacion_mm") else None

        necesita, cantidad, frecuencia, momento, justif, reco, urgencia = recomendar_riego(
            hum_suelo, temp, prec
        )

        registro = RecomendacionRiego(
            necesita_riego      = necesita,
            cantidad_litros_m2  = cantidad,
            frecuencia_dias     = frecuencia,
            momento_optimo      = momento,
            justificacion       = justif,
            recomendacion       = reco,
            nivel_urgencia      = urgencia,
            humedad_suelo_usada = hum_suelo,
            temperatura_usada   = temp,
            precipitacion_usada = prec,
            version_modelo      = "reglas-cenicafe-riego-1.0",
            id_cultivo          = cultivo_id,
            id_usuario          = usuario_id,
        )
        self.db.add(registro)
        self.db.commit()
        self.db.refresh(registro)

        return RecomendacionRiegoResponse(
            id_reco             = registro.id_reco,
            necesita_riego      = necesita,
            cantidad_litros_m2  = float(cantidad) if cantidad else None,
            frecuencia_dias     = frecuencia,
            momento_optimo      = momento,
            justificacion       = justif,
            recomendacion       = reco,
            nivel_urgencia      = urgencia,
            humedad_suelo_usada = hum_suelo,
            temperatura_usada   = temp,
            precipitacion_usada = prec,
            fecha_recomendacion = registro.fecha_recomendacion,
            id_cultivo          = cultivo_id,
        )

    # ----------------------------------------------------------
    # RF-09 - RECOMENDACION DE FERTILIZACION
    # ----------------------------------------------------------

    def recomendar_fertilizacion(
        self, cultivo_id: int, usuario_id: int
    ) -> RecomendacionFertResponse:
        """
        RF-09 + RN-03: genera recomendacion de fertilizacion
        basada en el estado quimico del suelo.
        """
        self._verificar_acceso_cultivo(cultivo_id, usuario_id)
        _, sue = self._verificar_rn03(cultivo_id, requiere_ambiental=False, requiere_suelo=True)

        ph   = float(sue["ph"])               if sue and sue.get("ph")               else None
        n    = float(sue["nitrogeno"])         if sue and sue.get("nitrogeno")         else None
        p    = float(sue["fosforo"])           if sue and sue.get("fosforo")           else None
        k    = float(sue["potasio"])           if sue and sue.get("potasio")           else None
        mo   = float(sue["materia_organica"])  if sue and sue.get("materia_organica")  else None

        tipo_f, dosis, frecuencia, metodo, defic, justif, reco, urgencia = recomendar_fertilizacion(
            ph, n, p, k, mo
        )

        registro = RecomendacionFertilizacion(
            tipo_fertilizante        = tipo_f,
            dosis_kg_ha              = dosis,
            frecuencia_aplicacion    = frecuencia,
            metodo_aplicacion        = metodo,
            nutrientes_deficientes   = json.dumps(defic, ensure_ascii=False),
            justificacion            = justif,
            recomendacion            = reco,
            nivel_urgencia           = urgencia,
            ph_suelo_usado           = ph,
            nitrogeno_usado          = n,
            fosforo_usado            = p,
            potasio_usado            = k,
            materia_organica_usada   = mo,
            version_modelo           = "reglas-cenicafe-fert-1.0",
            id_cultivo               = cultivo_id,
            id_usuario               = usuario_id,
        )
        self.db.add(registro)
        self.db.commit()
        self.db.refresh(registro)

        return RecomendacionFertResponse(
            id_reco_fert              = registro.id_reco_fert,
            tipo_fertilizante         = tipo_f,
            dosis_kg_ha               = float(dosis) if dosis else None,
            frecuencia_aplicacion     = frecuencia,
            metodo_aplicacion         = metodo,
            nutrientes_deficientes    = defic,
            justificacion             = justif,
            recomendacion             = reco,
            nivel_urgencia            = urgencia,
            ph_suelo_usado            = ph,
            nitrogeno_usado           = n,
            fosforo_usado             = p,
            potasio_usado             = k,
            materia_organica_usada    = mo,
            fecha_recomendacion       = registro.fecha_recomendacion,
            id_cultivo                = cultivo_id,
        )

    # ----------------------------------------------------------
    # RESUMEN DASHBOARD IA
    # ----------------------------------------------------------

    def resumen_ia(self, cultivo_id: int, usuario_id: int) -> ResumenIAResponse:
        """Panel consolidado del Caficultor con el estado de todos los modulos IA."""
        self._verificar_acceso_cultivo(cultivo_id, usuario_id)

        alertas            = []
        datos_validos      = False
        mensaje_rn03       = "Verifique los datos de monitoreo."

        # Verificar validez RN-03 sin lanzar excepcion
        try:
            amb = self._obtener_ultima_ambiental(cultivo_id)
            sue = self._obtener_ultima_suelo(cultivo_id)
            limite = timedelta(hours=settings.HORAS_DATOS_VALIDOS)
            ahora  = datetime.now(timezone.utc)
            amb_ok = False
            sue_ok = False

            if amb:
                fecha = amb["fecha_registro"]
                if fecha.tzinfo is None:
                    fecha = fecha.replace(tzinfo=timezone.utc)
                amb_ok = (ahora - fecha) <= limite

            if sue:
                fecha = sue["fecha_registro"]
                if fecha.tzinfo is None:
                    fecha = fecha.replace(tzinfo=timezone.utc)
                sue_ok = (ahora - fecha) <= limite

            datos_validos = amb_ok and sue_ok
            if datos_validos:
                mensaje_rn03 = "Datos actualizados. Todos los modelos de IA disponibles."
            else:
                mensaje_rn03 = (
                    "Datos desactualizados (> 24h). "
                    "Registre lecturas nuevas para habilitar recomendaciones de IA."
                )
                alertas.append("RN-03: Datos de monitoreo desactualizados")
        except Exception:
            pass

        # Ultimo analisis enfermedad
        ult_enf = (
            self.db.query(AnalisisImagen)
            .filter(
                AnalisisImagen.id_cultivo   == cultivo_id,
                AnalisisImagen.tipo_analisis == "enfermedad",
            )
            .order_by(AnalisisImagen.fecha_analisis.desc())
            .first()
        )

        # Ultimo analisis plaga
        ult_pla = (
            self.db.query(AnalisisImagen)
            .filter(
                AnalisisImagen.id_cultivo   == cultivo_id,
                AnalisisImagen.tipo_analisis == "plaga",
            )
            .order_by(AnalisisImagen.fecha_analisis.desc())
            .first()
        )

        # Ultima prediccion fito
        ult_fito = (
            self.db.query(PrediccionFitosanitaria)
            .filter(PrediccionFitosanitaria.id_cultivo == cultivo_id)
            .order_by(PrediccionFitosanitaria.fecha_prediccion.desc())
            .first()
        )

        # Ultima reco riego
        ult_riego = (
            self.db.query(RecomendacionRiego)
            .filter(RecomendacionRiego.id_cultivo == cultivo_id)
            .order_by(RecomendacionRiego.fecha_recomendacion.desc())
            .first()
        )

        # Ultima reco fertilizacion
        ult_fert = (
            self.db.query(RecomendacionFertilizacion)
            .filter(RecomendacionFertilizacion.id_cultivo == cultivo_id)
            .order_by(RecomendacionFertilizacion.fecha_recomendacion.desc())
            .first()
        )

        # Alertas activas
        if ult_enf and ult_enf.nivel_urgencia in ("alto", "critico"):
            alertas.append(
                f"Enfermedad detectada: {ult_enf.diagnostico} "
                f"(confianza {ult_enf.confianza * 100:.0f}%)"
            )
        if ult_pla and ult_pla.nivel_urgencia in ("alto", "critico"):
            alertas.append(
                f"Plaga detectada: {ult_pla.diagnostico} "
                f"(confianza {ult_pla.confianza * 100:.0f}%)"
            )
        if ult_fito and ult_fito.nivel_riesgo in ("alto", "critico"):
            alertas.append(
                f"Riesgo fitosanitario {ult_fito.nivel_riesgo.upper()}"
            )
        if ult_riego and ult_riego.necesita_riego == "si" and ult_riego.nivel_urgencia == "alto":
            alertas.append("Riego urgente requerido")

        return ResumenIAResponse(
            cultivo_id                = cultivo_id,
            datos_validos_rn03        = datos_validos,
            mensaje_rn03              = mensaje_rn03,
            ultimo_dx_enfermedad      = ult_enf.diagnostico        if ult_enf  else None,
            ultima_conf_enfermedad    = ult_enf.confianza           if ult_enf  else None,
            ultimo_dx_plaga           = ult_pla.diagnostico         if ult_pla  else None,
            ultima_conf_plaga         = ult_pla.confianza           if ult_pla  else None,
            ultimo_nivel_riesgo       = ult_fito.nivel_riesgo       if ult_fito else None,
            ultima_reco_riego         = ult_riego.necesita_riego    if ult_riego else None,
            ultimo_fertilizante       = ult_fert.tipo_fertilizante  if ult_fert  else None,
            alertas                   = alertas,
            fecha_ultimo_analisis_img = ult_enf.fecha_analisis           if ult_enf  else None,
            fecha_ultima_prediccion   = ult_fito.fecha_prediccion         if ult_fito else None,
            fecha_ultima_reco_riego   = ult_riego.fecha_recomendacion     if ult_riego else None,
            fecha_ultima_reco_fert    = ult_fert.fecha_recomendacion      if ult_fert  else None,
        )
