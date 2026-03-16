# ==============================================================
# modulo_06_mercado / tests/test_mercado.py
# Pruebas unitarias — Módulo 06 Mercado
#
# Cobertura:
#   RF-13  Motor estadístico de precios: estadísticas, WMA-3,
#          tendencia, alertas, recomendaciones
#   RF-14  Motor de demanda: clasificación, recomendaciones
#   RNF-01 Rendimiento: cálculos < 5 s (operaciones O(n))
#   RNF-02 Textos legibles para no técnicos
#   RN-01  Control de roles (Comercializador)
#   Schemas Pydantic: validaciones de entrada
# ==============================================================

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from app.analisis.motor_mercado import (
    calcular_estadisticas_precios,
    calcular_variacion_porcentual,
    clasificar_nivel_demanda,
    clasificar_tendencia,
    formatear_variacion_label,
    generar_alerta_precio,
    generar_recomendacion_demanda,
    generar_recomendacion_precio,
    proyectar_wma3,
    ICONOS_TENDENCIA,
    NIVEL_DEMANDA_LABELS,
)
from app.schemas.mercado import PrecioCreate
from app.services.mercado_service import MercadoService
from app.models.mercado import PrecioMercado, AnalisisPrecio, AnalisisDemanda


# ==============================================================
# FIXTURES
# ==============================================================

def make_precio(
    fuente: str = "fnc",
    precio: float = 5200.0,
    fecha_offset_dias: int = 0,
) -> PrecioMercado:
    p = PrecioMercado()
    p.id_precio        = 1
    p.fuente           = fuente
    p.tipo_cafe        = "pergamino_seco"
    p.precio_cop_kg    = precio
    p.precio_usd_lb    = None
    p.variedad         = "castillo"
    p.categoria_calidad= "todas"
    p.region           = "Antioquia"
    p.notas            = None
    p.id_lote_origen   = None
    p.id_usuario       = 5
    p.fecha_precio     = datetime.utcnow() - timedelta(days=fecha_offset_dias)
    p.fecha_registro   = datetime.utcnow()
    return p


def make_db_mock(precios=None, analisis=None):
    db = MagicMock()
    db.query.return_value.filter.return_value.all.return_value = precios or []
    db.query.return_value.filter.return_value.order_by.return_value.first.return_value = analisis
    db.query.return_value.filter.return_value.order_by.return_value.all.return_value = precios or []
    db.execute.return_value.fetchone.return_value = None
    db.execute.return_value.fetchall.return_value = []
    db.add    = MagicMock()
    db.commit = MagicMock()
    db.flush  = MagicMock()
    db.refresh = MagicMock(side_effect=lambda obj: None)
    return db


# ==============================================================
# RF-13 — ESTADÍSTICAS DE PRECIOS
# ==============================================================

class TestEstadisticasPrecios:

    def test_lista_un_elemento_retorna_valores_iguales(self):
        prom, mini, maxi, rango = calcular_estadisticas_precios([5200.0])
        assert prom  == 5200.0
        assert mini  == 5200.0
        assert maxi  == 5200.0
        assert rango == 0.0

    def test_lista_vacia_lanza_value_error(self):
        with pytest.raises(ValueError):
            calcular_estadisticas_precios([])

    def test_promedio_correcto_tres_elementos(self):
        prom, _, _, _ = calcular_estadisticas_precios([4800.0, 5000.0, 5200.0])
        assert prom == 5000.0

    def test_minimo_y_maximo_correctos(self):
        _, mini, maxi, _ = calcular_estadisticas_precios([6000.0, 4500.0, 5250.0])
        assert mini == 4500.0
        assert maxi == 6000.0

    def test_rango_calculado_como_diferencia(self):
        _, _, _, rango = calcular_estadisticas_precios([4000.0, 6000.0])
        assert rango == 2000.0

    def test_precios_con_decimales(self):
        prom, _, _, _ = calcular_estadisticas_precios([5100.50, 5299.50])
        assert prom == 5200.0

    def test_lista_grande_rendimiento(self):
        """RNF-01: 10_000 precios deben calcularse sin error."""
        import time
        precios = [5000.0 + i * 0.1 for i in range(10_000)]
        inicio  = time.time()
        calcular_estadisticas_precios(precios)
        assert (time.time() - inicio) < 1.0  # muy por debajo de 5 s


# ==============================================================
# RF-13 — VARIACIÓN PORCENTUAL
# ==============================================================

class TestVariacionPorcentual:

    def test_subida_del_10_pct(self):
        var = calcular_variacion_porcentual(5500.0, 5000.0)
        assert var == 10.0

    def test_bajada_del_5_pct(self):
        var = calcular_variacion_porcentual(4750.0, 5000.0)
        assert var == -5.0

    def test_sin_cambio_es_cero(self):
        var = calcular_variacion_porcentual(5000.0, 5000.0)
        assert var == 0.0

    def test_precio_anterior_none_retorna_none(self):
        var = calcular_variacion_porcentual(5000.0, None)
        assert var is None

    def test_precio_anterior_cero_retorna_none(self):
        var = calcular_variacion_porcentual(5000.0, 0)
        assert var is None

    def test_resultado_redondeado_dos_decimales(self):
        var = calcular_variacion_porcentual(5333.33, 5000.0)
        assert isinstance(var, float)
        assert len(str(var).split(".")[-1]) <= 2


# ==============================================================
# RF-13 — PROYECCIÓN WMA-3
# ==============================================================

class TestProyeccionWMA3:

    def test_un_periodo_retorna_none(self):
        assert proyectar_wma3([5000.0]) is None

    def test_lista_vacia_retorna_none(self):
        assert proyectar_wma3([]) is None

    def test_dos_periodos_ponderacion_correcta(self):
        # pesos [1,2]: (1*4800 + 2*5200) / 3 = 15200/3 ≈ 5066.67
        resultado = proyectar_wma3([4800.0, 5200.0])
        assert resultado == round((1 * 4800.0 + 2 * 5200.0) / 3, 2)

    def test_tres_periodos_ponderacion_correcta(self):
        # pesos [1,2,3]: (1*4800+2*5000+3*5200)/6 = (4800+10000+15600)/6 = 30400/6 ≈ 5066.67
        resultado = proyectar_wma3([4800.0, 5000.0, 5200.0])
        esperado  = round((1 * 4800 + 2 * 5000 + 3 * 5200) / 6, 2)
        assert resultado == esperado

    def test_cuatro_periodos_usa_solo_ultimos_tres(self):
        """WMA-3 debe ignorar el primer elemento si hay más de 3."""
        r4 = proyectar_wma3([3000.0, 4800.0, 5000.0, 5200.0])
        r3 = proyectar_wma3([4800.0, 5000.0, 5200.0])
        assert r4 == r3

    def test_precios_ascendentes_proyectan_mayor(self):
        resultado = proyectar_wma3([4000.0, 4500.0, 5000.0])
        assert resultado > 4500.0

    def test_precios_descendentes_proyectan_menor(self):
        resultado = proyectar_wma3([5500.0, 5000.0, 4500.0])
        assert resultado < 5000.0


# ==============================================================
# RF-13 — CLASIFICACIÓN DE TENDENCIA
# ==============================================================

class TestClasificacionTendencia:

    def test_variacion_alta_positiva_es_alza(self):
        t = clasificar_tendencia(10.0, 100.0, 5000.0, umbral_pct=5.0)
        assert t == "alza"

    def test_variacion_alta_negativa_es_baja(self):
        t = clasificar_tendencia(-8.0, 100.0, 5000.0, umbral_pct=5.0)
        assert t == "baja"

    def test_rango_alto_sobre_promedio_es_volatil(self):
        # rango 900, promedio 5000 → 18% > 15%
        t = clasificar_tendencia(2.0, 900.0, 5000.0, umbral_pct=5.0)
        assert t == "volatil"

    def test_variacion_moderada_es_estable(self):
        t = clasificar_tendencia(2.0, 100.0, 5000.0, umbral_pct=5.0)
        assert t == "estable"

    def test_sin_variacion_previa_es_estable(self):
        t = clasificar_tendencia(None, 100.0, 5000.0)
        assert t == "estable"

    def test_iconos_cubren_todas_las_tendencias(self):
        for k in ("alza", "baja", "estable", "volatil"):
            assert k in ICONOS_TENDENCIA
            assert len(ICONOS_TENDENCIA[k]) > 0


# ==============================================================
# RF-13 — ALERTAS DE PRECIO
# ==============================================================

class TestAlertasPrecios:

    def test_variacion_sobre_umbral_activa_alerta(self):
        activa, msg = generar_alerta_precio(8.0, 5500.0, "alza", umbral_pct=5.0)
        assert activa  is True
        assert msg     is not None
        assert "subió" in msg

    def test_variacion_negativa_sobre_umbral_activa_alerta(self):
        activa, msg = generar_alerta_precio(-6.0, 4700.0, "baja", umbral_pct=5.0)
        assert activa  is True
        assert "bajó"  in msg

    def test_variacion_bajo_umbral_no_activa_alerta(self):
        activa, _ = generar_alerta_precio(3.0, 5200.0, "estable", umbral_pct=5.0)
        assert activa is False

    def test_tendencia_volatil_activa_alerta(self):
        activa, msg = generar_alerta_precio(2.0, 5200.0, "volatil", umbral_pct=5.0)
        assert activa is True
        assert "volatilidad" in msg.lower()

    def test_variacion_none_no_activa_alerta(self):
        activa, _ = generar_alerta_precio(None, 5200.0, "estable")
        assert activa is False

    def test_mensaje_alerta_contiene_precio_actual(self):
        _, msg = generar_alerta_precio(10.0, 5800.0, "alza", umbral_pct=5.0)
        assert "5.800" in msg or "5800" in msg


# ==============================================================
# RF-13 — RECOMENDACIÓN DE PRECIO
# ==============================================================

class TestRecomendacionPrecio:

    def test_tendencia_alza_recomienda_vender(self):
        reco, _ = generar_recomendacion_precio("alza", 5.0, 5500.0, 5200.0, None)
        assert "vender" in reco.lower() or "venta" in reco.lower()

    def test_tendencia_baja_recomienda_evaluar(self):
        reco, _ = generar_recomendacion_precio("baja", -6.0, 4800.0, 5200.0, None)
        assert any(w in reco.lower() for w in ("bajando", "evaluando", "evalúe", "liquidez"))

    def test_tendencia_volatil_sugiere_dividir_ventas(self):
        reco, _ = generar_recomendacion_precio("volatil", None, 5100.0, 5200.0, None)
        assert any(w in reco.lower() for w in ("divide", "parciales", "lotes parciales", "volatilidad"))

    def test_proyectado_incluido_en_texto_estable(self):
        reco, _ = generar_recomendacion_precio("estable", 0.5, 5200.0, 5200.0, 5350.0)
        assert "5.350" in reco or "5350" in reco

    def test_interpretacion_incluye_diferencial_fnc(self):
        _, inter = generar_recomendacion_precio("alza", 5.0, 5720.0, 5200.0, None)
        assert "fnc" in inter.lower() or "encima" in inter.lower() or "%" in inter


# ==============================================================
# RF-14 — CLASIFICACIÓN DE DEMANDA
# ==============================================================

class TestClasificacionDemanda:

    def test_muchos_lotes_venta_rapida_es_muy_alta(self):
        nivel = clasificar_nivel_demanda(12, 15.0, 5.0)
        assert nivel == "muy_alta"

    def test_cinco_lotes_venta_normal_es_alta(self):
        nivel = clasificar_nivel_demanda(5, 0.0, 15.0)
        assert nivel == "alta"

    def test_cero_lotes_es_baja(self):
        nivel = clasificar_nivel_demanda(0, None, None)
        assert nivel == "baja"

    def test_venta_muy_lenta_es_baja(self):
        nivel = clasificar_nivel_demanda(3, -5.0, 35.0)
        assert nivel == "baja"

    def test_variacion_muy_negativa_baja_demanda(self):
        nivel = clasificar_nivel_demanda(2, -15.0, 20.0)
        assert nivel == "baja"

    def test_niveles_labels_cubren_todos(self):
        for k in ("baja", "media", "alta", "muy_alta"):
            assert k in NIVEL_DEMANDA_LABELS
            assert len(NIVEL_DEMANDA_LABELS[k]) > 0


# ==============================================================
# RF-14 — RECOMENDACIÓN DE DEMANDA
# ==============================================================

class TestRecomendacionDemanda:

    def test_demanda_muy_alta_recomienda_acelerar(self):
        reco, _ = generar_recomendacion_demanda(
            "muy_alta", 15, 3000.0, 4.0, "excelso", 20.0
        )
        assert any(w in reco.lower() for w in ("acelere", "oportunidad", "alta"))

    def test_demanda_baja_recomienda_diversificar(self):
        reco, _ = generar_recomendacion_demanda(
            "baja", 0, 0.0, None, None, -20.0
        )
        assert any(w in reco.lower() for w in ("diversif", "alternativas", "canales", "baja"))

    def test_interpretacion_incluye_volumen(self):
        _, inter = generar_recomendacion_demanda(
            "alta", 8, 1600.0, 10.0, "supremo", 5.0
        )
        assert "8" in inter and "1.600" in inter or "1600" in inter

    def test_categoria_top_incluida_en_recomendacion(self):
        reco, _ = generar_recomendacion_demanda(
            "alta", 6, 900.0, 8.0, "supremo", 10.0
        )
        assert "supremo" in reco

    def test_variacion_negativa_incluida_en_texto_baja(self):
        reco, _ = generar_recomendacion_demanda(
            "baja", 1, 100.0, None, None, -25.0
        )
        assert "25" in reco


# ==============================================================
# VALIDACIONES DE ESQUEMAS PYDANTIC
# ==============================================================

class TestValidacionesEsquemas:

    def test_precio_negativo_lanza_error(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            PrecioCreate(
                fuente="fnc",
                precio_cop_kg=-100.0,
                fecha_precio=datetime.now(),
            )

    def test_precio_cero_lanza_error(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            PrecioCreate(
                fuente="fnc",
                precio_cop_kg=0.0,
                fecha_precio=datetime.now(),
            )

    def test_fuente_invalida_lanza_error(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            PrecioCreate(
                fuente="desconocida",
                precio_cop_kg=5200.0,
                fecha_precio=datetime.now(),
            )

    def test_tipo_cafe_invalido_lanza_error(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            PrecioCreate(
                fuente="fnc",
                tipo_cafe="tipo_inexistente",
                precio_cop_kg=5200.0,
                fecha_precio=datetime.now(),
            )

    def test_precio_valido_sin_error(self):
        p = PrecioCreate(
            fuente="fnc",
            tipo_cafe="pergamino_seco",
            precio_cop_kg=5400.0,
            fecha_precio=datetime(2025, 6, 1),
        )
        assert p.precio_cop_kg == 5400.0


# ==============================================================
# FORMATO DE LABELS (RNF-02)
# ==============================================================

class TestLabelsLegibles:

    def test_variacion_positiva_tiene_signo_mas(self):
        label = formatear_variacion_label(7.5)
        assert "+" in label
        assert "7.5" in label

    def test_variacion_negativa_sin_signo_mas(self):
        label = formatear_variacion_label(-4.2)
        assert "+" not in label
        assert "4.2" in label

    def test_variacion_none_retorna_none(self):
        assert formatear_variacion_label(None) is None

    def test_label_incluye_texto_periodo_anterior(self):
        label = formatear_variacion_label(3.0)
        assert "período anterior" in label or "periodo anterior" in label
