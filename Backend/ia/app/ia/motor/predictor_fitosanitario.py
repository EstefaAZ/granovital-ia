# ==============================================================
# modulo_04_ia / app/ia/motor/predictor_fitosanitario.py
# Motor de prediccion fitosanitaria - RF-07
#
# Predice el nivel de riesgo de enfermedades fungicas basandose
# en las variables ambientales actuales del cultivo.
#
# MODELO: clasificador de riesgo basado en reglas agronomicas
# derivadas de la literatura CENICAFE sobre condiciones
# favorables para Roya (Hemileia vastatrix) y otras enfermedades
# fungicas del cafe colombiano.
#
# En produccion se reemplaza con un modelo XGBoost o RandomForest
# entrenado con datos historicos de cultivos colombianos.
# La interfaz del motor permanece identica (RNF-08).
#
# VARIABLES DE ENTRADA:
#   temperatura      Celsius
#   humedad_relativa porcentaje
#   precipitacion_mm mm acumulados
#
# SALIDA:
#   nivel_riesgo     bajo | moderado | alto | critico
#   probabilidad     0.0 - 1.0
#   factores_riesgo  lista de condiciones detectadas
#   enfermedades_prob probabilidad por enfermedad
# ==============================================================

import logging
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ==============================================================
# UMBRALES AGRONOMICOS DE RIESGO
# Roya del Cafeto: optima a 21-25C y HR > 80%
# Mancha de Hierro: favorecida por alta humedad y sombrío
# ==============================================================

UMBRALES = {
    # Temperatura critica para Roya (18-25 C optimo)
    "temp_roya_min":   18.0,
    "temp_roya_max":   25.0,
    # Humedad critica para enfermedades fungicas
    "hr_alerta":       75.0,
    "hr_critica":      90.0,
    # Precipitacion que favorece dispersion de esporas
    "precip_alerta":   10.0,
    "precip_critica":  30.0,
}

ENFERMEDADES_RIESGO = [
    "Roya (Hemileia vastatrix)",
    "Mancha de Hierro (Cercospora coffeicola)",
    "Antracnosis (Colletotrichum gloeosporioides)",
    "Ojo de Gallo (Mycena citricolor)",
]


def predecir_riesgo(
    temperatura:      Optional[float],
    humedad_relativa: Optional[float],
    precipitacion_mm: Optional[float],
) -> Tuple[str, float, List[str], Dict[str, float]]:
    """
    Calcula el nivel de riesgo fitosanitario basado en
    variables ambientales actuales.

    Retorna:
      nivel_riesgo     str  - bajo | moderado | alto | critico
      probabilidad     float
      factores_riesgo  list[str]
      enfermedades_prob dict {nombre: prob}
    """
    factores     = []
    puntuacion   = 0.0

    # Factor: temperatura en rango optimo para Roya
    if temperatura is not None:
        if UMBRALES["temp_roya_min"] <= temperatura <= UMBRALES["temp_roya_max"]:
            factores.append(
                f"Temperatura {temperatura}C en rango optimo para Roya ({UMBRALES['temp_roya_min']}-{UMBRALES['temp_roya_max']}C)"
            )
            puntuacion += 0.35

    # Factor: humedad relativa elevada
    if humedad_relativa is not None:
        if humedad_relativa >= UMBRALES["hr_critica"]:
            factores.append(
                f"Humedad relativa critica ({humedad_relativa}% >= {UMBRALES['hr_critica']}%) - favorece esporas"
            )
            puntuacion += 0.40
        elif humedad_relativa >= UMBRALES["hr_alerta"]:
            factores.append(
                f"Humedad relativa elevada ({humedad_relativa}% >= {UMBRALES['hr_alerta']}%)"
            )
            puntuacion += 0.20

    # Factor: precipitacion que dispersa esporas
    if precipitacion_mm is not None:
        if precipitacion_mm >= UMBRALES["precip_critica"]:
            factores.append(
                f"Precipitacion critica ({precipitacion_mm}mm) - dispersion activa de esporas"
            )
            puntuacion += 0.25
        elif precipitacion_mm >= UMBRALES["precip_alerta"]:
            factores.append(
                f"Precipitacion moderada ({precipitacion_mm}mm) - condicion humeda"
            )
            puntuacion += 0.10

    # Limitar puntuacion a 1.0
    puntuacion = min(puntuacion, 1.0)

    # Clasificar nivel
    if puntuacion >= 0.75:
        nivel = "critico"
    elif puntuacion >= 0.50:
        nivel = "alto"
    elif puntuacion >= 0.25:
        nivel = "moderado"
    else:
        nivel = "bajo"

    # Probabilidades por enfermedad (simplificado)
    factor_roya = 0.0
    if temperatura and UMBRALES["temp_roya_min"] <= temperatura <= UMBRALES["temp_roya_max"]:
        factor_roya += 0.4
    if humedad_relativa and humedad_relativa >= UMBRALES["hr_alerta"]:
        factor_roya += 0.4
    if precipitacion_mm and precipitacion_mm >= UMBRALES["precip_alerta"]:
        factor_roya += 0.2

    enfermedades_prob = {
        "Roya":          round(min(factor_roya, 1.0), 3),
        "Mancha_Hierro": round(min(puntuacion * 0.7, 1.0), 3),
        "Antracnosis":   round(min(puntuacion * 0.5, 1.0), 3),
        "Ojo_de_Gallo":  round(min(puntuacion * 0.3, 1.0), 3),
    }

    if not factores:
        factores = ["Condiciones ambientales dentro de rangos normales"]

    logger.info(
        f"Prediccion fito: nivel={nivel} prob={puntuacion:.3f} "
        f"factores={len(factores)}"
    )
    return nivel, round(puntuacion, 4), factores, enfermedades_prob


def generar_recomendacion_fito(nivel: str, factores: List[str]) -> str:
    """Genera recomendacion textual segun nivel de riesgo."""
    base = {
        "bajo": (
            "Condiciones de bajo riesgo fitosanitario. "
            "Mantenga monitoreo semanal y aplique fungicidas preventivos "
            "cada 30 dias en hojas jovenes durante floracion."
        ),
        "moderado": (
            "Riesgo moderado detectado. "
            "1) Incremente la frecuencia de monitoreo a dos veces por semana. "
            "2) Prepare aplicacion preventiva de fungicida de contacto (Clorotalonil 2 kg/ha). "
            "3) Revise el archivo fotografico del lote para comparar con semanas anteriores."
        ),
        "alto": (
            "RIESGO ALTO de infeccion fungica. Accion requerida esta semana. "
            "1) Aplique fungicida sistemico (Trifloxistrobina + Tebuconazol) 0.75 L/ha. "
            "2) Realice defoliacion sanitaria de hojas con lesiones. "
            "3) Suba imagen al modulo de deteccion para confirmar diagnostico. "
            "4) Registre la intervencion en el modulo de trazabilidad."
        ),
        "critico": (
            "NIVEL CRITICO: condiciones ideales para epidemia fungica. "
            "Intervencion INMEDIATA necesaria. "
            "1) Aplique fungicida sistemico de alta eficacia HOY. "
            "2) Suspenda temporalmente el riego por aspersion. "
            "3) Fotografe hojas y analicelas en el modulo de IA. "
            "4) Contacte al asesor tecnico del comite de cafeteros. "
            "5) Documente todo en el sistema de trazabilidad."
        ),
    }
    return base.get(nivel, base["moderado"])
