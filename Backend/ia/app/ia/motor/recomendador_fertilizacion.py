# ==============================================================
# modulo_04_ia / app/ia/motor/recomendador_fertilizacion.py
# Motor de recomendacion de fertilizacion - RF-09
#
# Recomienda tipo, dosis y metodo de aplicacion de fertilizante
# segun el estado quimico del suelo (pH, N, P, K, M.O.)
#
# Referencia: CENICAFE - Fertilizacion del Cafeto (2010).
# Plan de fertilizacion basado en analisis de suelo y
# curvas de respuesta para Coffea arabica en Colombia.
# ==============================================================

import logging
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Minimos criticos para cafe (mg/kg Bray II)
MIN_NITROGENO        = 20.0
MIN_FOSFORO          = 15.0
MIN_POTASIO          = 20.0
MIN_MATERIA_ORGANICA = 3.0

# pH optimo
PH_MIN_OPTIMO = 5.5
PH_MAX_OPTIMO = 6.5


def _calcular_deficiencias(
    nitrogeno:        Optional[float],
    fosforo:          Optional[float],
    potasio:          Optional[float],
    materia_organica: Optional[float],
    ph:               Optional[float],
) -> List[str]:
    """Determina cuales nutrientes estan por debajo del minimo critico."""
    defic = []
    if nitrogeno        is not None and nitrogeno        < MIN_NITROGENO:
        defic.append("N")
    if fosforo          is not None and fosforo          < MIN_FOSFORO:
        defic.append("P")
    if potasio          is not None and potasio          < MIN_POTASIO:
        defic.append("K")
    if materia_organica is not None and materia_organica < MIN_MATERIA_ORGANICA:
        defic.append("M.O.")
    if ph is not None and (ph < PH_MIN_OPTIMO or ph > PH_MAX_OPTIMO):
        defic.append("pH")
    return defic


# Catalogo de fertilizantes segun deficiencia predominante
FERTILIZANTES = {
    # Solo nitrogeno
    frozenset(["N"]): {
        "tipo":      "Urea (46-0-0)",
        "dosis":     150.0,
        "frecuencia": "Cada 3 meses en dosis fraccionadas",
        "metodo":    "edafico",
        "reco": (
            "Deficiencia de Nitrogeno detectada. "
            "Aplique Urea al 46% a razon de 150 kg/ha/año fraccionada en 3 aplicaciones. "
            "Aplique en corona alrededor del tallo, no en contacto directo con raices. "
            "Incorpore con riego o lluvia para evitar volatilizacion."
        ),
    },
    # Solo fosforo
    frozenset(["P"]): {
        "tipo":      "DAP - Fosfato Diamonico (18-46-0)",
        "dosis":     100.0,
        "frecuencia": "Una vez al año al inicio de lluvias",
        "metodo":    "edafico",
        "reco": (
            "Deficiencia de Fosforo detectada. "
            "Aplique DAP a razon de 100 kg/ha. "
            "El fosforo es poco movil en el suelo; incorpore superficialmente "
            "en la zona de raices activas (0-20 cm). "
            "Si el pH es acido (< 5.5) corrija primero con cal dolomitica."
        ),
    },
    # Solo potasio
    frozenset(["K"]): {
        "tipo":      "KCl - Cloruro de Potasio (0-0-60)",
        "dosis":     120.0,
        "frecuencia": "Cada 6 meses",
        "metodo":    "edafico",
        "reco": (
            "Deficiencia de Potasio detectada. "
            "Aplique KCl a razon de 120 kg/ha dividido en 2 aplicaciones semestrales. "
            "El potasio es clave para la calidad del grano y la tolerancia a sequia. "
            "Aplique en epocas de lluvia moderada para asegurar disolucion."
        ),
    },
    # N y P
    frozenset(["N", "P"]): {
        "tipo":      "DAP (18-46-0) + Urea complementaria",
        "dosis":     200.0,
        "frecuencia": "DAP al inicio de lluvias; Urea cada 3 meses",
        "metodo":    "edafico",
        "reco": (
            "Deficiencias de N y P detectadas simultaneamente. "
            "Aplique plan de fertilizacion combinado: "
            "1) DAP 100 kg/ha al inicio del primer periodo de lluvias. "
            "2) Urea 150 kg/ha/año en 3 aplicaciones trimestrales. "
            "Monitoree pH para asegurar disponibilidad de fosforo."
        ),
    },
    # N y K
    frozenset(["N", "K"]): {
        "tipo":      "Fertilizante completo 17-6-18-2 (N-P-K-Mg)",
        "dosis":     300.0,
        "frecuencia": "Tres aplicaciones al año",
        "metodo":    "edafico",
        "reco": (
            "Deficiencias de N y K detectadas. "
            "Aplique fertilizante completo 17-6-18-2 a 300 kg/ha/año "
            "en 3 aplicaciones de 100 kg/ha cada una. "
            "Este fertilizante balanceado es el mas recomendado por CENICAFE "
            "para cafetales colombianos en produccion."
        ),
    },
    # NPK completo
    frozenset(["N", "P", "K"]): {
        "tipo":      "Fertilizante Triple 15 (15-15-15) + corrector de pH",
        "dosis":     400.0,
        "frecuencia": "4 aplicaciones al año (cada 3 meses)",
        "metodo":    "edafico",
        "reco": (
            "Deficiencias multiples de N, P y K. Plan urgente requerido. "
            "1) Corrija el pH con cal dolomitica si esta por debajo de 5.5. "
            "2) Aplique fertilizante Triple 15 a 400 kg/ha/año. "
            "3) Complemente con micronutrientes (boro, zinc) via foliar. "
            "4) Repita analisis de suelo en 6 meses para evaluar respuesta."
        ),
    },
    # pH alterado
    frozenset(["pH"]): {
        "tipo":      "Cal dolomitica (CaMg(CO3)2) o Azufre agricola",
        "dosis":     500.0,
        "frecuencia": "Una aplicacion; evaluar pH a los 3 meses",
        "metodo":    "edafico",
        "reco": (
            "pH del suelo fuera del rango optimo (5.5-6.5). "
            "Si pH < 5.5: Aplique cal dolomitica a 500-1000 kg/ha segun acidez. "
            "Si pH > 6.5: Aplique azufre agricola a 200-400 kg/ha. "
            "La correccion del pH es la intervencion mas costo-efectiva "
            "pues mejora la disponibilidad de todos los nutrientes."
        ),
    },
}

FERTILIZANTE_DEFAULT = {
    "tipo":      "Fertilizante completo 17-6-18-2 (N-P-K-Mg)",
    "dosis":     300.0,
    "frecuencia": "Tres aplicaciones al año",
    "metodo":    "edafico",
    "reco": (
        "No se detectaron deficiencias criticas en los nutrientes evaluados. "
        "Mantenga el plan de fertilizacion preventiva con fertilizante completo "
        "17-6-18-2 a dosis de mantenimiento (200 kg/ha/año). "
        "Realice analisis de suelo certificado cada 2 años."
    ),
}


def recomendar_fertilizacion(
    ph:               Optional[float],
    nitrogeno:        Optional[float],
    fosforo:          Optional[float],
    potasio:          Optional[float],
    materia_organica: Optional[float],
) -> Tuple[str, Optional[float], Optional[str], str, List[str], str, str, str]:
    """
    Genera recomendacion de fertilizacion.

    Retorna:
      tipo_fertilizante      str
      dosis_kg_ha            float | None
      frecuencia_aplicacion  str | None
      metodo_aplicacion      str
      nutrientes_deficientes list[str]
      justificacion          str
      recomendacion          str
      nivel_urgencia         'bajo' | 'medio' | 'alto'
    """
    deficiencias = _calcular_deficiencias(
        nitrogeno, fosforo, potasio, materia_organica, ph
    )

    # Buscar el fertilizante mas especifico para las deficiencias detectadas
    clave    = frozenset(deficiencias)
    entrada  = FERTILIZANTES.get(clave)

    # Si no hay coincidencia exacta, buscar subconjunto
    if not entrada and deficiencias:
        for k, v in sorted(FERTILIZANTES.items(), key=lambda x: -len(x[0])):
            if k.issubset(clave) and k:
                entrada = v
                break

    if not entrada:
        entrada = FERTILIZANTE_DEFAULT

    # Urgencia
    if len(deficiencias) >= 3:
        urgencia = "alto"
    elif len(deficiencias) >= 1:
        urgencia = "medio"
    else:
        urgencia = "bajo"

    # Justificacion
    if deficiencias:
        partes = []
        if "N" in deficiencias:
            partes.append(f"Nitrogeno bajo ({nitrogeno} mg/kg, minimo {MIN_NITROGENO})")
        if "P" in deficiencias:
            partes.append(f"Fosforo bajo ({fosforo} mg/kg, minimo {MIN_FOSFORO})")
        if "K" in deficiencias:
            partes.append(f"Potasio bajo ({potasio} mg/kg, minimo {MIN_POTASIO})")
        if "M.O." in deficiencias:
            partes.append(f"Materia organica baja ({materia_organica}%, minimo {MIN_MATERIA_ORGANICA}%)")
        if "pH" in deficiencias:
            partes.append(f"pH fuera del rango optimo ({ph}, optimo {PH_MIN_OPTIMO}-{PH_MAX_OPTIMO})")
        justificacion = "Deficiencias detectadas: " + "; ".join(partes) + "."
    else:
        justificacion = (
            "Perfil nutricional del suelo dentro de rangos aceptables. "
            "Fertilizacion de mantenimiento recomendada."
        )

    logger.info(
        f"Reco fertilizacion: defic={deficiencias} "
        f"fertilizante='{entrada['tipo']}' urgencia={urgencia}"
    )

    return (
        entrada["tipo"],
        entrada["dosis"],
        entrada["frecuencia"],
        entrada["metodo"],
        deficiencias,
        justificacion,
        entrada["reco"],
        urgencia,
    )
