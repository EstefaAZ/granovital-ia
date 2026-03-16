# ==============================================================
# modulo_06_mercado / app/analisis/motor_mercado.py
# Motor estadístico de análisis de mercado
#
# RF-13  Análisis de precios: WMA-3, tendencia, proyección, alertas
# RF-14  Análisis de demanda: KPIs del período, nivel, variación
# RNF-01 Todo cálculo < 5 segundos (operaciones O(n), n moderado)
# RNF-02 Textos interpretativos legibles para no técnicos
#
# METODOLOGÍA DE PROYECCIÓN — Promedio Móvil Ponderado (WMA-3):
#   Usa los últimos 3 períodos con pesos [1, 2, 3] (más reciente
#   con mayor peso). Es el método apropiado para series cortas
#   de datos de precios agrícolas sin suficientes observaciones
#   para entrenar modelos ARIMA o similares.
#   Referencia: Box, G.E.P. & Jenkins, G.M. (1970). Time Series
#   Analysis: Forecasting and Control. Holden-Day.
#
# CLASIFICACIÓN DE TENDENCIA:
#   alza    variación > +UMBRAL
#   baja    variación < -UMBRAL
#   volatil rango > 15% del precio promedio
#   estable en los demás casos
# ==============================================================

from typing import List, Optional, Tuple
from app.core.config import settings


# ==============================================================
# RF-13 — ANÁLISIS DE PRECIOS
# ==============================================================

ICONOS_TENDENCIA = {
    "alza":    "↑",
    "baja":    "↓",
    "estable": "→",
    "volatil": "~",
}

LABELS_TENDENCIA = {
    "alza":    "Tendencia al alza",
    "baja":    "Tendencia a la baja",
    "estable": "Precio estable",
    "volatil": "Precio volátil",
}

NIVEL_DEMANDA_LABELS = {
    "baja":     "Demanda Baja ↓",
    "media":    "Demanda Media →",
    "alta":     "Demanda Alta ↑",
    "muy_alta": "Demanda Muy Alta ↑↑",
}


def calcular_estadisticas_precios(
    precios: List[float],
) -> Tuple[float, float, float, float]:
    """
    Calcula media, mínimo, máximo y rango de una lista de precios.
    Retorna (promedio, minimo, maximo, rango).
    Lanza ValueError si la lista está vacía.
    """
    if not precios:
        raise ValueError("Se necesita al menos un precio para calcular estadísticas.")
    promedio = round(sum(precios) / len(precios), 2)
    minimo   = round(min(precios), 2)
    maximo   = round(max(precios), 2)
    rango    = round(maximo - minimo, 2)
    return promedio, minimo, maximo, rango


def calcular_variacion_porcentual(
    precio_actual:  float,
    precio_anterior: float,
) -> Optional[float]:
    """
    Calcula la variación porcentual entre dos precios.
    Retorna None si el precio anterior es cero o None.
    """
    if not precio_anterior or precio_anterior == 0:
        return None
    return round((precio_actual - precio_anterior) / precio_anterior * 100, 2)


def proyectar_wma3(periodos: List[float]) -> Optional[float]:
    """
    Proyección por Promedio Móvil Ponderado de 3 períodos (WMA-3).
    Pesos: [1, 2, 3] — el período más reciente tiene mayor peso.

    Si hay menos de 2 períodos disponibles retorna None porque
    la proyección no sería estadísticamente confiable.

    Complejidad: O(1) — siempre opera sobre máximo 3 valores.
    """
    if len(periodos) < 2:
        return None
    # Tomar los últimos 3 (o menos si no hay suficientes)
    ultimos  = periodos[-3:]
    pesos    = list(range(1, len(ultimos) + 1))   # [1,2] o [1,2,3]
    suma_w   = sum(p * v for p, v in zip(pesos, ultimos))
    suma_den = sum(pesos)
    return round(suma_w / suma_den, 2)


def clasificar_tendencia(
    variacion_pct: Optional[float],
    rango:         float,
    promedio:      float,
    umbral_pct:    float = None,
) -> str:
    """
    Clasifica la tendencia del precio.

    Criterios:
      volatil: rango > 15% del promedio (alta dispersión)
      alza:    variación > +umbral
      baja:    variación < -umbral
      estable: demás casos
    """
    umbral = umbral_pct or settings.UMBRAL_VARIACION_ALERTA_PCT

    if promedio > 0 and (rango / promedio * 100) > 15.0:
        return "volatil"
    if variacion_pct is not None:
        if variacion_pct > umbral:
            return "alza"
        if variacion_pct < -umbral:
            return "baja"
    return "estable"


def generar_alerta_precio(
    variacion_pct:  Optional[float],
    precio_actual:  float,
    tendencia:      str,
    umbral_pct:     float = None,
) -> Tuple[bool, Optional[str]]:
    """
    Genera alerta cuando la variación supera el umbral configurado.
    Retorna (activa: bool, mensaje: str | None).
    """
    umbral = umbral_pct or settings.UMBRAL_VARIACION_ALERTA_PCT

    if variacion_pct is None:
        return False, None

    abs_var = abs(variacion_pct)
    if abs_var >= umbral:
        direccion = "subió" if variacion_pct > 0 else "bajó"
        return True, (
            f"El precio {direccion} un {abs_var:.1f}% respecto al período anterior. "
            f"Precio actual: ${precio_actual:,.0f}/kg. "
            f"Revise su estrategia de venta."
        )
    if tendencia == "volatil":
        return True, (
            f"Alta volatilidad detectada en los precios. "
            f"Precio actual: ${precio_actual:,.0f}/kg. "
            "Considere ventas anticipadas o contratos a precio fijo."
        )
    return False, None


def formatear_variacion_label(variacion_pct: Optional[float]) -> Optional[str]:
    """Genera texto legible de variación para la interfaz (RNF-02)."""
    if variacion_pct is None:
        return None
    signo = "+" if variacion_pct >= 0 else ""
    return f"{signo}{variacion_pct:.1f}% vs período anterior"


def generar_recomendacion_precio(
    tendencia:          str,
    variacion_pct:      Optional[float],
    precio_promedio:    float,
    precio_fnc_ref:     float,
    precio_proyectado:  Optional[float],
) -> Tuple[str, str]:
    """
    Genera recomendación comercial y texto de interpretación.
    Retorna (recomendacion, interpretacion).
    """
    diferencial = round(
        (precio_promedio - precio_fnc_ref) / precio_fnc_ref * 100, 1
    ) if precio_fnc_ref > 0 else 0.0

    dif_texto = (
        f"El precio promedio está {abs(diferencial):.1f}% "
        f"{'por encima' if diferencial >= 0 else 'por debajo'} del precio FNC de referencia."
    )

    if tendencia == "alza":
        reco = (
            "Los precios están en tendencia ascendente. "
            "Es un buen momento para vender si tiene stock aprobado. "
            "Considere negociar contratos a precio de mercado actual."
        )
        inter = f"Mercado favorable para el vendedor. {dif_texto}"
    elif tendencia == "baja":
        reco = (
            "Los precios están bajando. "
            "Evalúe si tiene urgencia de liquidez antes de vender. "
            "Si puede esperar, monitoree la recuperación del precio."
        )
        inter = f"Mercado desfavorable temporalmente. {dif_texto}"
    elif tendencia == "volatil":
        reco = (
            "El mercado muestra alta volatilidad. "
            "Divida las ventas en lotes parciales para promediar el precio. "
            "Considere contratos a precio fijo con compradores de confianza."
        )
        inter = f"Mercado inestable. {dif_texto}"
    else:  # estable
        reco = (
            "Precios estables en el período analizado. "
            "Momento adecuado para planificar ventas con anticipación. "
        )
        if precio_proyectado:
            reco += f"Precio proyectado próximo mes: ${precio_proyectado:,.0f}/kg."
        inter = f"Condiciones de mercado predecibles. {dif_texto}"

    return reco, inter


# ==============================================================
# RF-14 — ANÁLISIS DE DEMANDA
# ==============================================================

def clasificar_nivel_demanda(
    total_lotes:     int,
    variacion_pct:   Optional[float],
    dias_prom_venta: Optional[float],
) -> str:
    """
    Clasifica el nivel de demanda combinando tres indicadores:
      - Volumen de lotes vendidos en el período
      - Variación respecto al período anterior
      - Velocidad de venta (días promedio lote aprobado → vendido)

    Clasificación:
      muy_alta: muchos lotes + venta rápida (< 7 días) + en alza
      alta:     buen volumen o venta rápida
      baja:     pocos lotes o venta muy lenta (> 30 días) o en baja
      media:    demás casos
    """
    # Velocidad de venta es el indicador más sensible
    venta_rapida = dias_prom_venta is not None and dias_prom_venta < 7
    venta_lenta  = dias_prom_venta is not None and dias_prom_venta > 30
    en_alza      = variacion_pct is not None and variacion_pct > 10
    en_baja      = variacion_pct is not None and variacion_pct < -10

    if total_lotes >= 10 and (venta_rapida or en_alza):
        return "muy_alta"
    if total_lotes >= 5 or venta_rapida:
        return "alta"
    if total_lotes == 0 or venta_lenta or en_baja:
        return "baja"
    return "media"


def generar_recomendacion_demanda(
    nivel:           str,
    total_lotes:     int,
    kg_totales:      float,
    dias_prom:       Optional[float],
    categoria_top:   Optional[str],
    variacion_pct:   Optional[float],
) -> Tuple[str, str]:
    """
    Genera recomendación e interpretación de demanda.
    Retorna (recomendacion, interpretacion).
    """
    vol_texto = (
        f"Se vendieron {total_lotes} lote(s) "
        f"con {kg_totales:,.0f} kg en el período."
    )
    vel_texto = (
        f"Tiempo promedio de venta: {dias_prom:.0f} días."
        if dias_prom else ""
    )
    cat_texto = (
        f"La categoría más demandada fue '{categoria_top}'."
        if categoria_top else ""
    )

    if nivel == "muy_alta":
        reco = (
            "Demanda muy alta. Acelere la preparación de lotes para no perder "
            "oportunidades. Considere precios ligeramente superiores al mercado. "
            f"{cat_texto}"
        )
        inter = f"Mercado con alta actividad compradora. {vol_texto} {vel_texto}"
    elif nivel == "alta":
        reco = (
            "Buena actividad de demanda en el período. "
            "Mantenga la calidad y los tiempos de entrega acordados. "
            f"{cat_texto}"
        )
        inter = f"Demanda sostenida. {vol_texto} {vel_texto}"
    elif nivel == "baja":
        reco = (
            "Demanda baja en el período. "
            "Evalúe alternativas: diversificar compradores, mejorar la categoría "
            "del grano, explorar canales de exportación directa o cafés especiales. "
            f"{cat_texto}"
        )
        if variacion_pct and variacion_pct < 0:
            reco += f" La demanda cayó un {abs(variacion_pct):.1f}% vs el período anterior."
        inter = f"Mercado con baja actividad. {vol_texto} {vel_texto}"
    else:  # media
        reco = (
            "Demanda moderada y estable. "
            "Continúe con su estrategia comercial actual. "
            f"{cat_texto}"
        )
        inter = f"Actividad comercial normal. {vol_texto} {vel_texto}"

    return reco, inter
