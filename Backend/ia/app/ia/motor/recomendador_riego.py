# ==============================================================
# modulo_04_ia / app/ia/motor/recomendador_riego.py
# Motor de recomendacion de riego - RF-08
#
# Genera recomendaciones automaticas de riego basadas en:
#   - humedad_suelo    (tbl_monitoreo_suelo)
#   - temperatura      (tbl_monitoreo_ambiental)
#   - precipitacion_mm (tbl_monitoreo_ambiental)
#
# RN-03: el servicio valida que los datos sean < 24h antes
# de llamar a este motor.
#
# Referencia agronomica: CENICAFE - Manual del Cafetero
# Colombiano (2013). Cap. 8: Manejo del Agua en Cafe.
# ==============================================================

import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# Rangos de referencia CENICAFE
HUMEDAD_CRITICA_BAJA  = 30.0   # % - riesgo estres hidrico severo
HUMEDAD_BAJA          = 45.0   # % - inicio de deficit hidrico
HUMEDAD_OPTIMA_MIN    = 55.0   # % - rango optimo cafe
HUMEDAD_OPTIMA_MAX    = 75.0   # % - rango optimo cafe
HUMEDAD_ALTA          = 85.0   # % - riesgo de pudriccion radicular
TEMP_ALTA             = 28.0   # C - aumenta evapotranspiracion
PRECIP_SUFICIENTE     = 8.0    # mm - lluvia que reemplaza riego


def recomendar_riego(
    humedad_suelo:    Optional[float],
    temperatura:      Optional[float],
    precipitacion_mm: Optional[float],
) -> Tuple[str, Optional[float], Optional[int], Optional[str], str, str, str]:
    """
    Genera recomendacion de riego.

    Retorna:
      necesita_riego     'si' | 'no' | 'condicional'
      cantidad_litros_m2 float | None
      frecuencia_dias    int | None
      momento_optimo     str | None
      justificacion      str
      recomendacion      str
      nivel_urgencia     'bajo' | 'medio' | 'alto'
    """
    necesita      = "condicional"
    cantidad      = None
    frecuencia    = None
    momento       = None
    justificacion = ""
    urgencia      = "medio"

    partes = []

    # Lluvia reciente suficiente
    lluvia_suficiente = (
        precipitacion_mm is not None
        and precipitacion_mm >= PRECIP_SUFICIENTE
    )

    if lluvia_suficiente:
        partes.append(
            f"Precipitacion reciente de {precipitacion_mm}mm supera el umbral "
            f"minimo de {PRECIP_SUFICIENTE}mm. El suelo deberia tener humedad suficiente."
        )
        necesita   = "no"
        urgencia   = "bajo"
        frecuencia = 3

    if humedad_suelo is not None:
        if humedad_suelo < HUMEDAD_CRITICA_BAJA:
            partes.append(
                f"Humedad del suelo CRITICA ({humedad_suelo}% < {HUMEDAD_CRITICA_BAJA}%). "
                "Riesgo inminente de marchitez permanente."
            )
            necesita  = "si"
            cantidad  = 6.0
            frecuencia = 1
            momento   = "manana"
            urgencia  = "alto"
        elif humedad_suelo < HUMEDAD_BAJA:
            partes.append(
                f"Humedad del suelo baja ({humedad_suelo}%). "
                f"Por debajo del optimo ({HUMEDAD_OPTIMA_MIN}-{HUMEDAD_OPTIMA_MAX}%)."
            )
            if not lluvia_suficiente:
                necesita  = "si"
                cantidad  = 4.0
                frecuencia = 2
                momento   = "manana"
                urgencia  = "medio"
        elif humedad_suelo > HUMEDAD_ALTA:
            partes.append(
                f"Humedad del suelo muy alta ({humedad_suelo}%). "
                "Riesgo de anoxia radicular y enfermedades fungicas del suelo."
            )
            necesita  = "no"
            urgencia  = "medio"
        else:
            partes.append(
                f"Humedad del suelo en rango optimo ({humedad_suelo}%). "
                f"Optimo para cafe: {HUMEDAD_OPTIMA_MIN}-{HUMEDAD_OPTIMA_MAX}%."
            )
            if not lluvia_suficiente:
                necesita  = "condicional"
                frecuencia = 3
                urgencia  = "bajo"

    # Factor temperatura alta
    if temperatura is not None and temperatura > TEMP_ALTA:
        partes.append(
            f"Temperatura alta ({temperatura}C > {TEMP_ALTA}C) incrementa "
            "la evapotranspiracion. Aumente la frecuencia de riego."
        )
        if necesita == "condicional":
            necesita = "si"
        if frecuencia:
            frecuencia = max(1, frecuencia - 1)

    if not partes:
        partes = ["No se tienen datos suficientes para una recomendacion precisa."]
        necesita  = "condicional"
        urgencia  = "bajo"

    justificacion = " ".join(partes)

    # Generar recomendacion legible
    if necesita == "si":
        reco = (
            f"Se recomienda RIEGO. "
            f"Cantidad: {cantidad or 4.0} L/m2. "
            f"Frecuencia: cada {frecuencia or 2} dia(s). "
            f"Momento optimo: {momento or 'manana'} para minimizar evaporacion. "
            "Use riego por goteo o microaspersion para mayor eficiencia."
        )
    elif necesita == "no":
        reco = (
            "No se recomienda riego en este momento. "
            f"Proxima evaluacion en {frecuencia or 3} dia(s). "
            "Monitoree la humedad del suelo diariamente."
        )
    else:
        reco = (
            "Evaluacion condicional. "
            "Monitoree la humedad del suelo en las proximas 12 horas. "
            f"Si cae por debajo de {HUMEDAD_BAJA}%, aplique riego de 3-4 L/m2 "
            "en las horas de la manana."
        )

    logger.info(f"Reco riego: necesita={necesita} urgencia={urgencia}")
    return necesita, cantidad, frecuencia, momento, justificacion, reco, urgencia
