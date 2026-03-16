# ==============================================================
# modulo_05_trazabilidad / tests/test_trazabilidad.py
# Pruebas unitarias — Modulo 05 Trazabilidad
#
# Cobertura del Test Plan:
#   CP-04  Registro de lote (RF-10)
#   RF-10  Ciclo de vida completo y Diagrama de Estados
#   RF-11  Alertas de temperatura y humedad de secado
#   RF-12  Clasificacion FNC del grano
#   RN-02  Trazabilidad obligatoria antes de venta
#   RN-04  Inmutabilidad de registros validados
#   RN-05  Consulta publica limitada
#   RNF-05 Integridad del hash
# ==============================================================

import json
import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch, call

from app.schemas.trazabilidad import (
    ClasificacionCreate, LoteCreate, LoteUpdate,
    SecadoCreate,
)
from app.services.trazabilidad_service import (
    TrazabilidadService, _clasificar_grano_fnc,
    DESCRIPCIONES_CATEGORIA,
)
from app.util.qr_generator import generar_url_qr
from app.util.hash_integridad import calcular_hash_lote, verificar_hash_lote
from app.models.trazabilidad import TrazabilidadLote, ESTADOS_LOTE
from app.core.config import settings


# ==============================================================
# FIXTURES
# ==============================================================

def make_lote(
    estado: str = "registrado",
    clasificacion: str = "sin_clasificar",
    validado: bool = False,
    numero_defectos: int = None,
    humedad: float = None,
) -> TrazabilidadLote:
    """Fabrica un objeto TrazabilidadLote para pruebas."""
    lote = TrazabilidadLote()
    lote.id_lote               = 1
    lote.codigo_lote           = "GV-2025-0001"
    lote.variedad_cafe         = "castillo"
    lote.fecha_cosecha         = datetime(2025, 6, 15)
    lote.metodo_cosecha        = "manual_selectiva"
    lote.kg_cereza_cosechados  = 500.0
    lote.clasificacion_calidad = clasificacion
    lote.estado                = estado
    lote.validado              = validado
    lote.numero_defectos       = numero_defectos
    lote.humedad_final_pct     = humedad
    lote.id_cultivo            = 1
    lote.id_usuario_creador    = 10
    lote.fecha_creacion        = datetime.utcnow()
    lote.hash_integridad       = None
    lote.codigo_qr             = None
    lote.puntaje_taza          = None
    lote.observaciones         = None
    lote.metodo_beneficio      = None
    lote.kg_pergamino_seco     = None
    lote.precio_venta_kg       = None
    lote.comprador             = None
    lote.fecha_venta           = None
    lote.destino_exportacion   = None
    lote.fecha_actualizacion   = None
    return lote


def make_db_mock(lote: TrazabilidadLote = None):
    """DB mock con lote configurable."""
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = lote
    db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
    db.execute.return_value.fetchone.return_value = MagicMock()
    db.add    = MagicMock()
    db.commit = MagicMock()
    db.flush  = MagicMock()
    db.refresh = MagicMock(side_effect=lambda obj: None)
    return db


# ==============================================================
# CP-04 / RF-10 — ESTADOS DEL LOTE (Diagrama de Estados)
# ==============================================================

class TestDiagramaEstados:

    def test_estados_definidos_incluyen_todos_del_diagrama(self):
        """El catalogo de estados debe incluir los 7 del diagrama oficial."""
        esperados = {
            "registrado", "disponible", "en_analisis",
            "aprobado", "con_problema", "vendido", "eliminado",
        }
        assert esperados.issubset(set(ESTADOS_LOTE))

    def test_confirmar_lote_transicion_registrado_a_disponible(self):
        """confirmarRegistro: Registrado -> Disponible."""
        from fastapi import HTTPException
        lote = make_lote("registrado")
        db   = make_db_mock(lote)
        svc  = TrazabilidadService(db)

        resultado = svc.confirmar_lote(1, 10)
        assert resultado.estado_anterior == "registrado"
        assert resultado.estado_nuevo    == "disponible"
        assert lote.estado               == "disponible"

    def test_confirmar_lote_ya_disponible_lanza_409(self):
        """Confirmar un lote que ya esta 'disponible' debe lanzar HTTP 409."""
        from fastapi import HTTPException
        lote = make_lote("disponible")
        db   = make_db_mock(lote)
        svc  = TrazabilidadService(db)

        with pytest.raises(HTTPException) as exc:
            svc.confirmar_lote(1, 10)
        assert exc.value.status_code == 409

    def test_confirmar_lote_aprobado_lanza_409(self):
        """Confirmar un lote 'aprobado' debe lanzar HTTP 409."""
        from fastapi import HTTPException
        lote = make_lote("aprobado")
        db   = make_db_mock(lote)
        svc  = TrazabilidadService(db)

        with pytest.raises(HTTPException) as exc:
            svc.confirmar_lote(1, 10)
        assert exc.value.status_code == 409

    def test_lote_no_encontrado_lanza_404(self):
        """Intentar acceder a un lote inexistente debe lanzar HTTP 404."""
        from fastapi import HTTPException
        db  = make_db_mock(None)   # sin lote
        svc = TrazabilidadService(db)

        with pytest.raises(HTTPException) as exc:
            svc.obtener_lote(999, 10)
        assert exc.value.status_code == 404

    def test_acceso_de_otro_usuario_lanza_403(self):
        """Acceder a lote de otro usuario debe lanzar HTTP 403."""
        from fastapi import HTTPException
        lote = make_lote()
        lote.id_usuario_creador = 99   # diferente al solicitante
        db   = make_db_mock(lote)
        svc  = TrazabilidadService(db)

        with pytest.raises(HTTPException) as exc:
            svc.obtener_lote(1, 10)   # usuario 10, lote de usuario 99
        assert exc.value.status_code == 403


# ==============================================================
# RN-02 — TRAZABILIDAD OBLIGATORIA ANTES DE VENTA
# ==============================================================

class TestRN02TrazabilidadObligatoria:

    def test_venta_lote_no_aprobado_lanza_409(self):
        """RN-02: no se puede vender un lote en estado 'disponible'."""
        from fastapi import HTTPException
        lote = make_lote("disponible")
        db   = make_db_mock(lote)
        svc  = TrazabilidadService(db)

        with pytest.raises(HTTPException) as exc:
            svc.registrar_venta(1, 10, "Comprador SA", 5500.0)
        assert exc.value.status_code == 409
        assert "RN-02" in exc.value.detail

    def test_venta_lote_en_analisis_lanza_409(self):
        """RN-02: no se puede vender un lote en estado 'en_analisis'."""
        from fastapi import HTTPException
        lote = make_lote("en_analisis")
        db   = make_db_mock(lote)
        svc  = TrazabilidadService(db)

        with pytest.raises(HTTPException) as exc:
            svc.registrar_venta(1, 10, "Exportadora", 5200.0)
        assert exc.value.status_code == 409
        assert "RN-02" in exc.value.detail

    def test_venta_lote_sin_clasificacion_lanza_422(self):
        """RN-02: un lote 'aprobado' sin clasificacion no puede venderse."""
        from fastapi import HTTPException
        lote = make_lote("aprobado", clasificacion="sin_clasificar")
        db   = make_db_mock(lote)
        svc  = TrazabilidadService(db)

        with pytest.raises(HTTPException) as exc:
            svc.registrar_venta(1, 10, "Cooperativa", 5000.0)
        assert exc.value.status_code == 422
        assert "RN-02" in exc.value.detail

    def test_venta_lote_aprobado_con_clasificacion_exitosa(self):
        """RN-02: un lote aprobado con clasificacion puede venderse."""
        lote = make_lote("aprobado", clasificacion="excelso")
        db   = make_db_mock(lote)
        svc  = TrazabilidadService(db)

        resultado = svc.registrar_venta(1, 10, "Almacafe", 5400.0, "Alemania")
        assert resultado.estado_nuevo    == "vendido"
        assert resultado.estado_anterior == "aprobado"
        assert lote.estado               == "vendido"
        assert lote.comprador            == "Almacafe"

    def test_venta_registra_evento_inmutable(self):
        """La venta debe registrar un evento en el log."""
        lote = make_lote("aprobado", clasificacion="excelso")
        db   = make_db_mock(lote)
        svc  = TrazabilidadService(db)

        svc.registrar_venta(1, 10, "Cooperativa", 5200.0)
        assert db.add.called


# ==============================================================
# RN-04 — INMUTABILIDAD DE TRAZABILIDAD
# ==============================================================

class TestRN04Inmutabilidad:

    def test_modificar_lote_validado_sin_ser_admin_lanza_409(self):
        """RN-04: un Productor no puede modificar un lote validado."""
        from fastapi import HTTPException
        lote         = make_lote("aprobado")
        lote.validado = True
        db   = make_db_mock(lote)
        svc  = TrazabilidadService(db)

        datos = LoteUpdate(observaciones="cambio no autorizado")
        with pytest.raises(HTTPException) as exc:
            svc.actualizar_lote(1, datos, 10, es_admin=False)
        assert exc.value.status_code == 409
        assert "RN-04" in exc.value.detail

    def test_modificar_lote_validado_siendo_admin_permite(self):
        """RN-04: un Administrador puede modificar lotes validados."""
        lote          = make_lote("aprobado")
        lote.validado = True
        db            = make_db_mock(lote)
        svc           = TrazabilidadService(db)

        datos = LoteUpdate(observaciones="correccion administrativa")
        # No debe lanzar excepcion
        try:
            svc.actualizar_lote(1, datos, 10, es_admin=True)
        except Exception as e:
            pytest.fail(f"Admin no deberia recibir excepcion: {e}")

    def test_lote_no_validado_puede_modificarse(self):
        """Un lote en estado 'registrado' sin validar puede modificarse."""
        lote          = make_lote("registrado")
        lote.validado = False
        db            = make_db_mock(lote)
        svc           = TrazabilidadService(db)

        datos = LoteUpdate(observaciones="ajuste normal")
        try:
            svc.actualizar_lote(1, datos, 10, es_admin=False)
        except Exception as e:
            pytest.fail(f"No debia lanzar excepcion: {e}")


# ==============================================================
# RF-11 — ALERTAS DE SECADO
# ==============================================================

class TestAlertasSecado:

    def _svc(self):
        return TrazabilidadService(MagicMock())

    def test_temperatura_critica_genera_alerta_critica(self):
        """Temperatura > 55C debe generar alerta critica."""
        svc   = self._svc()
        alerta = svc._alerta_temperatura_secado(58.0)
        assert alerta is not None
        assert "CRITICO" in alerta or "critica" in alerta.lower() or "55" in alerta

    def test_temperatura_alta_genera_alerta_alta(self):
        """Temperatura > 45C (pero <= 55C) debe generar alerta de exceso."""
        svc   = self._svc()
        alerta = svc._alerta_temperatura_secado(50.0)
        assert alerta is not None

    def test_temperatura_optima_sin_alerta(self):
        """Temperatura entre 35 y 45C no debe generar alerta."""
        svc   = self._svc()
        alerta = svc._alerta_temperatura_secado(40.0)
        assert alerta is None

    def test_temperatura_baja_genera_alerta_baja(self):
        """Temperatura < 35C debe generar alerta de proceso lento."""
        svc   = self._svc()
        alerta = svc._alerta_temperatura_secado(28.0)
        assert alerta is not None
        assert "bajo" in alerta.lower() or "lento" in alerta.lower() or "35" in alerta

    def test_humedad_objetivo_sin_alerta(self):
        """Humedad en o por debajo del 11% no genera alerta."""
        svc   = self._svc()
        alerta = svc._alerta_humedad_secado(10.5)
        assert alerta is None

    def test_humedad_alta_genera_alerta_inicial(self):
        """Humedad > 40% debe informar que el proceso esta en etapa inicial."""
        svc   = self._svc()
        alerta = svc._alerta_humedad_secado(45.0)
        assert alerta is not None

    def test_humedad_cercana_objetivo_genera_aviso(self):
        """Humedad entre 11 y 13% debe generar aviso de proximidad al objetivo."""
        svc   = self._svc()
        alerta = svc._alerta_humedad_secado(12.5)
        assert alerta is not None
        assert "11%" in alerta or "objetivo" in alerta.lower() or "cerca" in alerta.lower()

    def test_humedad_none_sin_alerta(self):
        """Sin lectura de humedad no se genera alerta."""
        svc   = self._svc()
        alerta = svc._alerta_humedad_secado(None)
        assert alerta is None

    def test_proceso_completo_cuando_humedad_objetivo_y_horas_minimas(self):
        """El secado esta completo cuando humedad <= 11% y horas >= 72."""
        proceso_ok = (
            10.5 <= settings.SECADO_HUMEDAD_OBJETIVO
            and 80 >= settings.SECADO_HORAS_MINIMAS
        )
        assert proceso_ok is True

    def test_proceso_incompleto_sin_horas_minimas(self):
        """Con humedad OK pero solo 40h el proceso no esta completo."""
        proceso_ok = (
            10.5 <= settings.SECADO_HUMEDAD_OBJETIVO
            and 40 >= settings.SECADO_HORAS_MINIMAS
        )
        assert proceso_ok is False


# ==============================================================
# RF-12 — CLASIFICACION FNC DEL GRANO
# ==============================================================

class TestClasificacionFNC:

    def test_cero_defectos_humedad_optima_es_supremo(self):
        """0 defectos + humedad 11% = Supremo."""
        cat, aprobado, precio = _clasificar_grano_fnc(0, 11.0, None)
        assert cat      == "supremo"
        assert aprobado is True
        assert precio   > 0

    def test_cuatro_defectos_es_excelso_extra(self):
        """4 defectos = Excelso Extra."""
        cat, aprobado, precio = _clasificar_grano_fnc(4, 11.5, None)
        assert cat      == "excelso_extra"
        assert aprobado is True

    def test_ocho_defectos_es_excelso(self):
        """8 defectos = Excelso (estandar exportacion)."""
        cat, aprobado, precio = _clasificar_grano_fnc(8, 12.0, None)
        assert cat      == "excelso"
        assert aprobado is True

    def test_doce_defectos_es_corriente(self):
        """12 defectos = Corriente (no apto exportacion)."""
        cat, aprobado, precio = _clasificar_grano_fnc(12, 11.0, None)
        assert cat      == "corriente"
        assert aprobado is False

    def test_muchos_defectos_es_pasilla(self):
        """30 defectos = Pasilla."""
        cat, aprobado, precio = _clasificar_grano_fnc(30, 11.0, None)
        assert cat      == "pasilla"
        assert aprobado is False

    def test_humedad_alta_degrada_categoria(self):
        """Humedad 14% (> 12%) con 0 defectos no es Supremo."""
        cat, aprobado, precio = _clasificar_grano_fnc(0, 14.0, None)
        assert cat != "supremo"   # degradado por humedad

    def test_humedad_muy_baja_es_pasilla(self):
        """Humedad 6% (< 8%) = Pasilla por deshidratacion."""
        cat, aprobado, precio = _clasificar_grano_fnc(0, 6.0, None)
        assert cat == "pasilla"

    def test_puntaje_taza_80_incrementa_precio(self):
        """Puntaje SCA >= 80 debe dar precio premium (+15%)."""
        _, _, precio_sin  = _clasificar_grano_fnc(0, 11.0, None)
        _, _, precio_con  = _clasificar_grano_fnc(0, 11.0, 82.0)
        assert precio_con > precio_sin

    def test_todas_categorias_tienen_descripcion(self):
        """Cada categoria FNC debe tener descripcion legible."""
        for cat in ("supremo", "excelso_extra", "excelso", "corriente", "pasilla"):
            assert cat in DESCRIPCIONES_CATEGORIA
            assert len(DESCRIPCIONES_CATEGORIA[cat]) > 10

    def test_clasificacion_supremo_activa_estado_aprobado(self):
        """Clasificar como supremo debe transicionar a estado 'aprobado'."""
        lote = make_lote("en_analisis")
        db   = make_db_mock(lote)
        svc  = TrazabilidadService(db)

        datos = ClasificacionCreate(
            numero_defectos=0, humedad_pct=11.0, metodo="manual"
        )
        resultado = svc.clasificar_grano(1, datos, 10)
        assert resultado.estado_lote_nuevo  == "aprobado"
        assert resultado.aprobado_exportacion is True
        assert lote.estado                  == "aprobado"
        assert lote.validado                is True

    def test_clasificacion_pasilla_activa_estado_con_problema(self):
        """Clasificar como pasilla debe transicionar a estado 'con_problema'."""
        lote = make_lote("en_analisis")
        db   = make_db_mock(lote)
        svc  = TrazabilidadService(db)

        datos = ClasificacionCreate(
            numero_defectos=35, humedad_pct=11.0, metodo="manual"
        )
        resultado = svc.clasificar_grano(1, datos, 10)
        assert resultado.estado_lote_nuevo    == "con_problema"
        assert resultado.aprobado_exportacion is False
        assert lote.estado                    == "con_problema"

    def test_clasificar_lote_eliminado_lanza_409(self):
        """No se puede clasificar un lote eliminado."""
        from fastapi import HTTPException
        lote = make_lote("eliminado")
        db   = make_db_mock(lote)
        svc  = TrazabilidadService(db)

        datos = ClasificacionCreate(numero_defectos=2, humedad_pct=11.0)
        with pytest.raises(HTTPException) as exc:
            svc.clasificar_grano(1, datos, 10)
        assert exc.value.status_code == 409


# ==============================================================
# RNF-05 — INTEGRIDAD DEL HASH (RN-04)
# ==============================================================

class TestHashIntegridad:

    def test_hash_generado_es_64_caracteres_hexadecimales(self):
        """El hash SHA-256 debe tener exactamente 64 caracteres hex."""
        h = calcular_hash_lote(
            "GV-2025-0001", "castillo", "2025-06-15",
            500.0, "excelso", 11.5, 3, "sal-test"
        )
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

    def test_mismo_input_produce_mismo_hash(self):
        """El hash debe ser determinista para el mismo input."""
        args = ("GV-2025-0002", "colombia", "2025-07-01",
                300.0, "supremo", 10.8, 0, "sal")
        assert calcular_hash_lote(*args) == calcular_hash_lote(*args)

    def test_cambio_en_defectos_cambia_hash(self):
        """Cambiar el numero de defectos debe producir un hash diferente."""
        h1 = calcular_hash_lote("GV-01", "castillo", "2025-01-01",
                                 100.0, "excelso", 11.0, 3, "sal")
        h2 = calcular_hash_lote("GV-01", "castillo", "2025-01-01",
                                 100.0, "excelso", 11.0, 5, "sal")
        assert h1 != h2

    def test_cambio_en_categoria_cambia_hash(self):
        """Cambiar la categoria de calidad debe cambiar el hash."""
        h1 = calcular_hash_lote("GV-02", "castillo", "2025-01-01",
                                 200.0, "supremo", 11.0, 0, "sal")
        h2 = calcular_hash_lote("GV-02", "castillo", "2025-01-01",
                                 200.0, "excelso", 11.0, 0, "sal")
        assert h1 != h2

    def test_verificacion_exitosa_datos_integros(self):
        """verificar_hash_lote retorna True cuando el registro no fue alterado."""
        args = ("GV-03", "caturra", "2025-02-01", 150.0, "excelso", 11.5, 4, "sal")
        hash_orig = calcular_hash_lote(*args)
        assert verificar_hash_lote(hash_orig, *args) is True

    def test_verificacion_falla_datos_alterados(self):
        """verificar_hash_lote retorna False cuando el registro fue alterado."""
        hash_orig = calcular_hash_lote(
            "GV-04", "castillo", "2025-03-01", 400.0, "supremo", 11.0, 0, "sal"
        )
        # Alterar numero de defectos
        assert verificar_hash_lote(
            hash_orig, "GV-04", "castillo", "2025-03-01",
            400.0, "supremo", 11.0, 2, "sal"
        ) is False

    def test_clasificacion_aprobada_genera_hash_en_lote(self):
        """Al aprobar un lote, debe generarse el hash de integridad."""
        lote = make_lote("en_analisis")
        db   = make_db_mock(lote)
        svc  = TrazabilidadService(db)

        datos = ClasificacionCreate(numero_defectos=2, humedad_pct=11.0, metodo="manual")
        svc.clasificar_grano(1, datos, 10)

        assert lote.hash_integridad is not None
        assert len(lote.hash_integridad) == 64


# ==============================================================
# RN-05 — CONSULTA PUBLICA QR
# ==============================================================

class TestRN05ConsultaPublica:

    def test_url_qr_contiene_codigo_lote(self):
        """La URL del QR debe contener el codigo del lote."""
        url = generar_url_qr("GV-2025-0001", "http://localhost:3000")
        assert "GV-2025-0001" in url

    def test_url_qr_contiene_url_base(self):
        """La URL del QR debe usar la URL base del sistema."""
        url = generar_url_qr("GV-2025-0001", "https://granovital.co")
        assert "granovital.co" in url

    def test_consulta_publica_lote_no_aprobado_lanza_404(self):
        """Un lote en estado 'en_analisis' no debe ser visible publicamente."""
        from fastapi import HTTPException
        lote = make_lote("en_analisis")
        lote.codigo_lote = "GV-2025-0001"
        db   = make_db_mock(lote)
        svc  = TrazabilidadService(db)

        with pytest.raises(HTTPException) as exc:
            svc.consulta_publica("GV-2025-0001")
        assert exc.value.status_code == 404

    def test_consulta_publica_lote_aprobado_retorna_info_publica(self):
        """Un lote aprobado debe retornar informacion publica valida."""
        lote = make_lote("aprobado", clasificacion="excelso")
        lote.codigo_lote    = "GV-2025-0001"
        lote.puntaje_taza   = 84.0
        lote.fecha_cosecha  = datetime(2025, 6, 1)
        db   = make_db_mock(lote)

        # Mock del execute para obtener municipio
        db.execute.return_value.fetchone.return_value = None

        svc  = TrazabilidadService(db)
        resp = svc.consulta_publica("GV-2025-0001")

        assert resp.codigo_lote == "GV-2025-0001"
        assert "excelso" in resp.clasificacion_calidad.lower()
        assert resp.puntaje_taza == 84.0
        # Debe NO incluir campos internos
        assert not hasattr(resp, "precio_venta_kg")
        assert not hasattr(resp, "id_usuario_creador")
        assert not hasattr(resp, "hash_integridad")

    def test_consulta_publica_lote_vendido_retorna_info(self):
        """Un lote vendido tambien debe ser consultable publicamente."""
        lote = make_lote("vendido", clasificacion="supremo")
        lote.codigo_lote   = "GV-2025-0002"
        lote.fecha_cosecha = datetime(2025, 5, 1)
        db   = make_db_mock(lote)
        db.execute.return_value.fetchone.return_value = None

        svc  = TrazabilidadService(db)
        resp = svc.consulta_publica("GV-2025-0002")

        assert resp.codigo_lote == "GV-2025-0002"
        assert "supremo" in resp.clasificacion_calidad.lower()

    def test_clasificacion_aprobada_genera_url_qr_en_lote(self):
        """Al aprobar un lote, se debe generar la URL del QR."""
        lote = make_lote("en_analisis")
        db   = make_db_mock(lote)
        svc  = TrazabilidadService(db)

        datos = ClasificacionCreate(numero_defectos=0, humedad_pct=11.0, metodo="manual")
        svc.clasificar_grano(1, datos, 10)

        assert lote.codigo_qr is not None
        assert lote.codigo_lote in lote.codigo_qr


# ==============================================================
# VALIDACIONES DE ESQUEMAS PYDANTIC
# ==============================================================

class TestValidacionesEsquemas:

    def test_lote_create_kg_negativo_lanza_error(self):
        """LoteCreate con kg negativos debe lanzar ValidationError."""
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            LoteCreate(
                variedad_cafe="castillo",
                fecha_cosecha=datetime.now(),
                kg_cereza_cosechados=-10.0,
                id_cultivo=1,
            )

    def test_lote_create_variedad_invalida_lanza_error(self):
        """LoteCreate con variedad desconocida debe lanzar ValidationError."""
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            LoteCreate(
                variedad_cafe="VARIEDAD_INVALIDA",
                fecha_cosecha=datetime.now(),
                kg_cereza_cosechados=100.0,
                id_cultivo=1,
            )

    def test_secado_create_temperatura_fuera_de_rango_lanza_error(self):
        """SecadoCreate con temperatura > 80C debe lanzar ValidationError."""
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            SecadoCreate(temperatura_c=95.0, horas_transcurridas=24)

    def test_secado_create_horas_negativas_lanza_error(self):
        """SecadoCreate con horas negativas debe lanzar ValidationError."""
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            SecadoCreate(temperatura_c=40.0, horas_transcurridas=-5)

    def test_clasificacion_defectos_negativos_lanza_error(self):
        """ClasificacionCreate con defectos negativos debe lanzar error."""
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            ClasificacionCreate(numero_defectos=-1, humedad_pct=11.0)

    def test_clasificacion_humedad_fuera_de_rango_lanza_error(self):
        """ClasificacionCreate con humedad > 30% debe lanzar error."""
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            ClasificacionCreate(numero_defectos=2, humedad_pct=35.0)

    def test_lote_create_valido_sin_error(self):
        """Un LoteCreate valido no debe lanzar excepciones."""
        try:
            LoteCreate(
                variedad_cafe="colombia",
                fecha_cosecha=datetime(2025, 6, 1),
                metodo_cosecha="manual_selectiva",
                kg_cereza_cosechados=250.0,
                id_cultivo=3,
            )
        except Exception as e:
            pytest.fail(f"No debia lanzar excepcion: {e}")
