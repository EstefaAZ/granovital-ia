# ==============================================================
# modulo_04_ia / tests/test_ia.py
# Pruebas unitarias - Modulo 04 Inteligencia Artificial
#
# Cobertura del Test Plan:
#   CP-05  Analisis de imagen IA (RF-05 enfermedad, RF-06 plaga)
#   CP-06  Recomendacion automatica (RF-07, RF-08, RF-09)
#   RN-03  Bloqueo por datos desactualizados
#   RNF-01 Tiempo de inferencia < 5 segundos
#   RNF-08 Recarga de modelos en caliente
# ==============================================================

import json
import io
import time
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch, AsyncMock

from app.ia.motor.clasificador_imagen import (
    ClasificadorImagen, ENFERMEDADES, PLAGAS, obtener_recomendacion,
)
from app.ia.motor.predictor_fitosanitario import (
    predecir_riesgo, generar_recomendacion_fito,
)
from app.ia.motor.recomendador_riego import recomendar_riego
from app.ia.motor.recomendador_fertilizacion import recomendar_fertilizacion
from app.schemas.analisis import AnalisisImagenResponse, ClaseConfianza


# ==============================================================
# FIXTURES
# ==============================================================

def imagen_bytes_mock(tamano: int = 5000) -> bytes:
    """Genera bytes de imagen simulada para pruebas."""
    return bytes([i % 256 for i in range(tamano)])


def db_mock_con_cultivo(
    horas_amb: float = 1.0,
    horas_sue: float = 1.0,
    sin_amb:   bool  = False,
    sin_sue:   bool  = False,
):
    """DB mock con lecturas de monitoreo configurables."""
    db = MagicMock()
    ahora = datetime.now(timezone.utc)

    # Acceso al cultivo
    db.execute.return_value.fetchone.return_value = MagicMock()

    def execute_side(query, params=None):
        q_str = str(query)
        mock_res = MagicMock()

        if "tbl_monitoreo_ambiental" in q_str:
            if sin_amb:
                mock_res.fetchone.return_value = None
            else:
                row = MagicMock()
                row._mapping = {
                    "temperatura":      22.0,
                    "humedad_relativa": 80.0,
                    "precipitacion_mm": 5.0,
                    "fecha_registro":   ahora - timedelta(hours=horas_amb),
                }
                mock_res.fetchone.return_value = row
        elif "tbl_monitoreo_suelo" in q_str:
            if sin_sue:
                mock_res.fetchone.return_value = None
            else:
                row = MagicMock()
                row._mapping = {
                    "ph":               6.2,
                    "humedad_suelo":    55.0,
                    "nitrogeno":        28.0,
                    "fosforo":          18.0,
                    "potasio":          22.0,
                    "materia_organica": 3.8,
                    "fecha_registro":   ahora - timedelta(hours=horas_sue),
                }
                mock_res.fetchone.return_value = row
        elif "tbl_cultivo" in q_str:
            mock_res.fetchone.return_value = MagicMock()
        return mock_res

    db.execute.side_effect = execute_side
    return db


# ==============================================================
# CP-05 - CLASIFICADOR DE IMAGEN (RF-05 y RF-06)
# ==============================================================

class TestClasificadorImagen:

    def test_cp05_clasificador_enfermedad_crea_correctamente(self):
        """CP-05: el clasificador de enfermedades debe instanciarse."""
        clf = ClasificadorImagen("enfermedad")
        assert clf.tipo == "enfermedad"
        assert clf.modo_simulado is True    # sin modelo en disco

    def test_cp05_clasificador_plaga_crea_correctamente(self):
        """CP-06: el clasificador de plagas debe instanciarse."""
        clf = ClasificadorImagen("plaga")
        assert clf.tipo == "plaga"

    def test_cp05_analisis_retorna_estructura_correcta(self):
        """La inferencia debe retornar (diagnostico, confianza, top, tiempo)."""
        clf = ClasificadorImagen("enfermedad")
        dx, conf, top, t = clf.analizar(imagen_bytes_mock(), "hoja.jpg")
        assert isinstance(dx,   str)
        assert 0.0 <= conf <= 1.0
        assert isinstance(top,  list)
        assert len(top) >= 1
        assert isinstance(t, float)
        assert t >= 0

    def test_cp05_diagnostico_pertenece_al_catalogo(self):
        """El diagnostico debe ser una clase conocida del catalogo."""
        clf = ClasificadorImagen("enfermedad")
        dx, _, _, _ = clf.analizar(imagen_bytes_mock(), "prueba.jpg")
        assert dx in ENFERMEDADES

    def test_cp06_diagnostico_plaga_pertenece_al_catalogo(self):
        """El diagnostico de plaga debe ser una clase conocida."""
        clf = ClasificadorImagen("plaga")
        dx, _, _, _ = clf.analizar(imagen_bytes_mock(), "fruto.jpg")
        assert dx in PLAGAS

    def test_cp05_top_clases_estructura_valida(self):
        """El top de clases debe tener clave 'clase' y 'probabilidad'."""
        clf = ClasificadorImagen("enfermedad")
        _, _, top, _ = clf.analizar(imagen_bytes_mock())
        for item in top:
            assert "clase"        in item
            assert "probabilidad" in item
            assert 0.0 <= item["probabilidad"] <= 1.0

    def test_cp05_probabilidades_suman_aproximadamente_1(self):
        """Las probabilidades del top deben ser plausibles (no suman > 1.1)."""
        clf = ClasificadorImagen("enfermedad")
        _, _, top, _ = clf.analizar(imagen_bytes_mock())
        total = sum(t["probabilidad"] for t in top)
        assert total <= 1.01    # top-3 no suman mas que 1

    def test_cp05_inferencia_reproducible(self):
        """El mismo input debe producir el mismo diagnostico (modo simulado)."""
        clf  = ClasificadorImagen("enfermedad")
        img  = imagen_bytes_mock(4000)
        dx1, conf1, _, _ = clf.analizar(img)
        dx2, conf2, _, _ = clf.analizar(img)
        assert dx1   == dx2
        assert conf1 == conf2

    def test_cp05_tiempo_inferencia_dentro_rnf01(self):
        """RNF-01: inferencia debe completarse en menos de 5 segundos."""
        clf   = ClasificadorImagen("enfermedad")
        inicio = time.perf_counter()
        clf.analizar(imagen_bytes_mock(10_000))
        elapsed = time.perf_counter() - inicio
        assert elapsed < 5.0, f"Inferencia tomo {elapsed:.2f}s, supera 5s"

    def test_rnf08_reload_no_lanza_excepcion(self):
        """RNF-08: la recarga del modelo no debe lanzar excepciones."""
        clf = ClasificadorImagen("enfermedad")
        try:
            clf.reload()
        except Exception as e:
            pytest.fail(f"reload() lanzo excepcion: {e}")

    def test_cp05_imagen_muy_pequena_simulada_no_falla(self):
        """Una imagen de 1 KB debe procesarse sin errores en modo simulado."""
        clf = ClasificadorImagen("plaga")
        dx, conf, top, t = clf.analizar(bytes(1200))
        assert dx in PLAGAS

    def test_cp05_todas_las_enfermedades_tienen_recomendacion(self):
        """Cada clase del catalogo de enfermedades debe tener recomendacion."""
        for clase in ENFERMEDADES:
            reco, urgencia = obtener_recomendacion("enfermedad", clase)
            assert len(reco) > 20
            assert urgencia in ("bajo", "medio", "alto", "critico")

    def test_cp06_todas_las_plagas_tienen_recomendacion(self):
        """Cada clase del catalogo de plagas debe tener recomendacion."""
        for clase in PLAGAS:
            reco, urgencia = obtener_recomendacion("plaga", clase)
            assert len(reco) > 20
            assert urgencia in ("bajo", "medio", "alto", "critico")

    def test_cp05_urgencia_roya_es_alto(self):
        """La Roya debe tener urgencia 'alto' por su impacto economico."""
        _, urgencia = obtener_recomendacion("enfermedad", "roya")
        assert urgencia == "alto"

    def test_cp06_urgencia_broca_es_critico(self):
        """La Broca del Cafe debe tener urgencia 'critico'."""
        _, urgencia = obtener_recomendacion("plaga", "broca")
        assert urgencia == "critico"

    def test_cp05_planta_sana_urgencia_bajo(self):
        """Una planta sana debe tener urgencia 'bajo'."""
        _, urgencia = obtener_recomendacion("enfermedad", "sano")
        assert urgencia == "bajo"


# ==============================================================
# RF-07 - PREDICCION FITOSANITARIA
# ==============================================================

class TestPrediccionFitosanitaria:

    def test_riesgo_alto_con_condiciones_roya(self):
        """HR 92% + temp 22C + lluvia 35mm = riesgo critico para Roya."""
        nivel, prob, factores, enf = predecir_riesgo(22.0, 92.0, 35.0)
        assert nivel in ("alto", "critico")
        assert prob  > 0.5
        assert len(factores) > 0

    def test_riesgo_bajo_con_condiciones_secas(self):
        """Temperatura 32C + HR 40% + sin lluvia = riesgo bajo."""
        nivel, prob, factores, enf = predecir_riesgo(32.0, 40.0, 0.0)
        assert nivel in ("bajo", "moderado")

    def test_riesgo_moderado_solo_humedad_alta(self):
        """Solo humedad alta sin temperatura optima = moderado."""
        nivel, prob, factores, enf = predecir_riesgo(30.0, 80.0, 3.0)
        assert nivel in ("moderado", "bajo")

    def test_probabilidad_entre_0_y_1(self):
        """La probabilidad de riesgo siempre debe estar entre 0 y 1."""
        for temp, hum, prec in [
            (15.0, 60.0, 0.0),
            (22.0, 95.0, 40.0),
            (35.0, 30.0, 0.0),
        ]:
            _, prob, _, _ = predecir_riesgo(temp, hum, prec)
            assert 0.0 <= prob <= 1.0

    def test_sin_datos_retorna_bajo(self):
        """Sin variables ambientales debe retornar nivel bajo."""
        nivel, prob, factores, enf = predecir_riesgo(None, None, None)
        assert nivel == "bajo"
        assert prob  == 0.0

    def test_factores_son_lista_de_strings(self):
        """Los factores de riesgo deben ser una lista de cadenas."""
        _, _, factores, _ = predecir_riesgo(22.0, 85.0, 15.0)
        assert isinstance(factores, list)
        for f in factores:
            assert isinstance(f, str)

    def test_enfermedades_prob_tiene_roya(self):
        """El diccionario de probabilidades debe incluir la Roya."""
        _, _, _, enf = predecir_riesgo(22.0, 88.0, 20.0)
        assert "Roya" in enf

    def test_recomendacion_critica_contiene_fungicida(self):
        """La recomendacion critica debe mencionar accion de fungicida."""
        reco = generar_recomendacion_fito("critico", ["humedad_alta"])
        assert "fungicida" in reco.lower() or "inmediata" in reco.lower()

    def test_recomendacion_bajo_es_preventiva(self):
        """Riesgo bajo debe generar recomendacion preventiva."""
        reco = generar_recomendacion_fito("bajo", [])
        assert "preventiv" in reco.lower() or "monitoreo" in reco.lower()


# ==============================================================
# RF-08 - RECOMENDACION DE RIEGO
# ==============================================================

class TestRecomendacionRiego:

    def test_humedad_critica_recomienda_riego_urgente(self):
        """Humedad 25% debe generar recomendacion de riego urgente."""
        necesita, cantidad, frec, momento, justif, reco, urgencia = recomendar_riego(
            25.0, 24.0, 0.0
        )
        assert necesita == "si"
        assert cantidad > 0
        assert urgencia == "alto"

    def test_humedad_optima_no_requiere_riego(self):
        """Humedad 65% sin temperatura alta debe dar condicional o no."""
        necesita, _, _, _, _, _, _ = recomendar_riego(65.0, 22.0, 2.0)
        assert necesita in ("no", "condicional")

    def test_lluvia_suficiente_no_requiere_riego(self):
        """Precipitacion de 15mm debe indicar que no se necesita riego."""
        necesita, _, _, _, _, _, _ = recomendar_riego(60.0, 22.0, 15.0)
        assert necesita in ("no", "condicional")

    def test_temperatura_alta_aumenta_urgencia(self):
        """Temperatura 32C con humedad 40% debe dar riego urgente."""
        necesita, _, _, _, justif, _, urgencia = recomendar_riego(40.0, 32.0, 0.0)
        assert necesita == "si"
        assert urgencia in ("medio", "alto")

    def test_sin_datos_retorna_condicional(self):
        """Sin datos disponibles debe retornar estado condicional."""
        necesita, _, _, _, _, _, _ = recomendar_riego(None, None, None)
        assert necesita == "condicional"

    def test_recomendacion_incluye_cantidad(self):
        """La recomendacion de riego debe incluir cantidad y frecuencia."""
        _, cantidad, frec, _, _, reco, _ = recomendar_riego(28.0, 26.0, 0.0)
        assert "L/m2" in reco or "riego" in reco.lower()

    def test_humedad_muy_alta_indica_no_regar(self):
        """Humedad de suelo 90% debe indicar no regar."""
        necesita, _, _, _, justif, _, _ = recomendar_riego(90.0, 20.0, 5.0)
        assert necesita == "no"
        assert "alta" in justif.lower() or "anoxia" in justif.lower()

    def test_momento_optimo_manana_en_urgencia(self):
        """Riego urgente debe recomendar la manana como momento optimo."""
        _, _, _, momento, _, _, urgencia = recomendar_riego(20.0, 30.0, 0.0)
        if urgencia == "alto":
            assert momento == "manana"


# ==============================================================
# RF-09 - RECOMENDACION DE FERTILIZACION
# ==============================================================

class TestRecomendacionFertilizacion:

    def test_deficiencia_nitrogeno_recomienda_urea(self):
        """Nitrogeno bajo con otros nutrientes OK debe recomendar Urea."""
        tipo, dosis, _, _, defic, justif, reco, urgencia = recomendar_fertilizacion(
            ph=6.0, nitrogeno=10.0, fosforo=20.0, potasio=25.0, materia_organica=4.0
        )
        assert "N" in defic
        assert "urea" in tipo.lower() or "nitro" in reco.lower()

    def test_deficiencia_ph_recomienda_cal(self):
        """pH 4.2 debe recomendar encalado."""
        tipo, _, _, metodo, defic, _, reco, _ = recomendar_fertilizacion(
            ph=4.2, nitrogeno=25.0, fosforo=20.0, potasio=25.0, materia_organica=4.0
        )
        assert "pH" in defic
        assert "cal" in reco.lower() or "ph" in reco.lower()

    def test_npk_completo_bajo_urgencia_alta(self):
        """N, P y K deficientes simultaneamente = urgencia alta."""
        _, _, _, _, defic, _, _, urgencia = recomendar_fertilizacion(
            ph=6.0, nitrogeno=5.0, fosforo=5.0, potasio=5.0, materia_organica=4.0
        )
        assert len(defic) >= 3
        assert urgencia == "alto"

    def test_suelo_optimo_urgencia_baja(self):
        """Suelo con todos los nutrientes sobre minimos = urgencia baja."""
        _, _, _, _, defic, _, _, urgencia = recomendar_fertilizacion(
            ph=6.2, nitrogeno=30.0, fosforo=25.0, potasio=28.0, materia_organica=4.5
        )
        assert urgencia == "bajo"
        assert len(defic) == 0

    def test_sin_datos_no_lanza_excepcion(self):
        """Llamar sin datos no debe lanzar excepcion."""
        try:
            recomendar_fertilizacion(None, None, None, None, None)
        except Exception as e:
            pytest.fail(f"Lanzo excepcion inesperada: {e}")

    def test_justificacion_menciona_deficiencias(self):
        """La justificacion debe mencionar los nutrientes deficientes."""
        _, _, _, _, defic, justif, _, _ = recomendar_fertilizacion(
            ph=6.0, nitrogeno=8.0, fosforo=20.0, potasio=25.0, materia_organica=4.0
        )
        assert "N" in defic
        assert "nitrogeno" in justif.lower() or "N" in justif

    def test_deficiencia_potasio_recomienda_kcl(self):
        """Solo potasio deficiente debe recomendar KCl."""
        tipo, _, _, _, defic, _, reco, _ = recomendar_fertilizacion(
            ph=6.0, nitrogeno=25.0, fosforo=20.0, potasio=10.0, materia_organica=4.0
        )
        assert "K" in defic
        assert "KCl" in tipo or "potasio" in reco.lower()

    def test_dosis_es_positiva(self):
        """La dosis recomendada debe ser siempre positiva."""
        _, dosis, _, _, _, _, _, _ = recomendar_fertilizacion(
            ph=5.0, nitrogeno=10.0, fosforo=10.0, potasio=10.0, materia_organica=2.0
        )
        assert dosis is not None
        assert dosis > 0


# ==============================================================
# RN-03 - BLOQUEO POR DATOS DESACTUALIZADOS
# ==============================================================

class TestRN03EnServicio:
    """
    Verifica que el IAService rechace correctamente las solicitudes
    cuando los datos del M03 superan el umbral de frescura.
    """

    def _crear_servicio(self, **kwargs):
        from app.services.ia_service import IAService
        db = db_mock_con_cultivo(**kwargs)
        # mock para queries ORM (resumen)
        db.query.return_value.filter.return_value.order_by.return_value.first.return_value = None
        db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []
        return IAService(db)

    def test_rn03_datos_frescos_no_bloquea_prediccion(self):
        """Con datos de 1h, la verificacion RN-03 no debe lanzar excepcion."""
        from fastapi import HTTPException
        svc = self._crear_servicio(horas_amb=1.0)
        try:
            amb, _ = svc._verificar_rn03(1, True, False)
            assert amb is not None
        except HTTPException:
            pytest.fail("No debia bloquear con datos de 1h")

    def test_rn03_datos_caducados_bloquea_prediccion(self):
        """Con datos de 30h, debe lanzar HTTP 422 con mensaje RN-03."""
        from fastapi import HTTPException
        svc = self._crear_servicio(horas_amb=30.0)
        with pytest.raises(HTTPException) as exc:
            svc._verificar_rn03(1, True, False)
        assert exc.value.status_code == 422
        assert "RN-03" in exc.value.detail

    def test_rn03_sin_datos_ambientales_bloquea(self):
        """Sin datos ambientales, debe lanzar HTTP 422."""
        from fastapi import HTTPException
        svc = self._crear_servicio(sin_amb=True)
        with pytest.raises(HTTPException) as exc:
            svc._verificar_rn03(1, True, False)
        assert exc.value.status_code == 422
        assert "RN-03" in exc.value.detail

    def test_rn03_sin_datos_suelo_bloquea_fertilizacion(self):
        """Sin datos de suelo, debe lanzar HTTP 422."""
        from fastapi import HTTPException
        svc = self._crear_servicio(sin_sue=True)
        with pytest.raises(HTTPException) as exc:
            svc._verificar_rn03(1, False, True)
        assert exc.value.status_code == 422

    def test_rn03_solo_suelo_desactualizado_bloquea(self):
        """Amb fresco pero suelo 48h debe bloquear."""
        from fastapi import HTTPException
        svc = self._crear_servicio(horas_amb=1.0, horas_sue=48.0)
        with pytest.raises(HTTPException) as exc:
            svc._verificar_rn03(1, False, True)
        assert exc.value.status_code == 422

    def test_rn03_mensaje_incluye_horas(self):
        """El mensaje de error debe indicar las horas transcurridas."""
        from fastapi import HTTPException
        svc = self._crear_servicio(horas_amb=36.0)
        with pytest.raises(HTTPException) as exc:
            svc._verificar_rn03(1, True, False)
        assert "horas" in exc.value.detail.lower() or "36" in exc.value.detail


# ==============================================================
# VALIDACION DE IMAGEN EN EL SERVICIO
# ==============================================================

class TestValidacionImagen:

    @pytest.mark.asyncio
    async def test_cp05_formato_invalido_rechazado(self):
        """Un archivo PDF enviado como imagen debe ser rechazado con 415."""
        from fastapi import HTTPException
        from app.services.ia_service import IAService

        db  = db_mock_con_cultivo()
        svc = IAService(db)

        imagen = MagicMock()
        imagen.content_type = "application/pdf"
        imagen.read         = AsyncMock(return_value=imagen_bytes_mock(5000))
        imagen.filename     = "documento.pdf"

        with pytest.raises(HTTPException) as exc:
            await svc.analizar_imagen(1, 10, "enfermedad", imagen)
        assert exc.value.status_code == 415

    @pytest.mark.asyncio
    async def test_cp05_imagen_demasiado_grande_rechazada(self):
        """Imagen de 11 MB debe ser rechazada con 413."""
        from fastapi import HTTPException
        from app.services.ia_service import IAService

        db  = db_mock_con_cultivo()
        svc = IAService(db)

        imagen = MagicMock()
        imagen.content_type = "image/jpeg"
        imagen.read         = AsyncMock(return_value=bytes(11 * 1024 * 1024))
        imagen.filename     = "enorme.jpg"

        with pytest.raises(HTTPException) as exc:
            await svc.analizar_imagen(1, 10, "enfermedad", imagen)
        assert exc.value.status_code == 413

    @pytest.mark.asyncio
    async def test_cp05_imagen_valida_retorna_respuesta(self):
        """Imagen JPEG valida debe retornar AnalisisImagenResponse."""
        from app.services.ia_service import IAService

        db  = db_mock_con_cultivo()
        db.add    = MagicMock()
        db.commit = MagicMock()
        db.refresh = MagicMock()

        # Simular objeto creado con id
        def refresh_side(obj):
            obj.id_analisis    = 99
            obj.fecha_analisis = datetime.utcnow()
        db.refresh.side_effect = refresh_side

        svc    = IAService(db)
        imagen = MagicMock()
        imagen.content_type = "image/jpeg"
        imagen.read         = AsyncMock(return_value=imagen_bytes_mock(8000))
        imagen.filename     = "hoja_cafe.jpg"

        resultado = await svc.analizar_imagen(1, 10, "enfermedad", imagen)

        assert resultado.id_analisis    == 99
        assert resultado.tipo_analisis  == "enfermedad"
        assert resultado.diagnostico    in ENFERMEDADES
        assert 0.0 <= resultado.confianza <= 1.0
        assert "%" in resultado.confianza_pct
        assert "s de" in resultado.tiempo_pct_rnf01
        db.add.assert_called_once()
        db.commit.assert_called_once()
