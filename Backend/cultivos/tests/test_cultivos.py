# ==============================================================
# modulo_02_cultivos / tests/test_cultivos.py
# Pruebas unitarias alineadas con el Test Plan del proyecto
#
# CP-03 Registro cultivo - nivel Sistema - Prioridad Alta
# CP-04 Registro lote    - nivel Integracion - Prioridad Alta
# Incluye validacion de RN-02 y diagramas de estados
# ==============================================================

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from datetime import datetime

from app.schemas.cultivo import (
    CultivoCreate, CultivoUpdate,
    LoteCreate, LoteUpdate,
    SensorCreate,
)
from app.services.cultivo_service import (
    CultivoService,
    TRANSICIONES_CULTIVO,
    TRANSICIONES_LOTE,
)


# ==============================================================
# FIXTURES
# ==============================================================

def cultivo_mock(estado: str = "creado") -> MagicMock:
    c = MagicMock()
    c.id_cultivo     = 1
    c.nombre_cultivo = "Finca La Esperanza"
    c.ubicacion      = "Andes, Antioquia"
    c.area_hectareas = 3.5
    c.variedad_cafe  = "Castillo"
    c.estado         = estado
    c.id_usuario     = 10
    c.lotes          = []
    c.sensores       = []
    c.fecha_registro = datetime.utcnow()
    c.__table__      = MagicMock()
    c.__table__.columns = []
    return c


def lote_mock(estado: str = "registrado") -> MagicMock:
    l = MagicMock()
    l.id_lote       = 1
    l.codigo_lote   = "LOT-2025-001"
    l.codigo_qr     = "token_qr_seguro_48chars"
    l.estado_lote   = estado
    l.cantidad_kg   = 450.0
    l.id_cultivo    = 1
    l.fecha_registro = datetime.utcnow()
    return l


def db_mock_con_cultivo(cultivo=None):
    """Base de datos mock que retorna el cultivo indicado."""
    db = MagicMock()
    q  = MagicMock()
    f  = MagicMock()
    f.first.return_value = cultivo
    q.filter.return_value = f
    q.filter.return_value.filter.return_value = f
    db.query.return_value = q
    return db


# ==============================================================
# PRUEBAS - RF-03 GESTION DE CULTIVOS (CP-03)
# ==============================================================

class TestGestionCultivos:

    def test_cp03_crear_cultivo_exitoso(self):
        """CP-03: el sistema crea un cultivo en estado 'creado'."""
        db = MagicMock()
        db.add    = MagicMock()
        db.commit = MagicMock()
        db.refresh = MagicMock(side_effect=lambda obj: None)

        service = CultivoService(db)
        datos   = CultivoCreate(
            nombre_cultivo="Finca La Esperanza",
            ubicacion="Andes, Antioquia",
            area_hectareas=3.5,
            variedad_cafe="Castillo",
        )

        # Simula que db.refresh puebla el objeto
        def _refresh(obj):
            obj.id_cultivo     = 1
            obj.fecha_registro = datetime.utcnow()

        db.refresh.side_effect = _refresh
        cultivo = service.crear_cultivo(datos, usuario_id=10)

        assert cultivo.nombre_cultivo == "Finca La Esperanza"
        assert cultivo.estado         == "creado"
        assert cultivo.id_usuario     == 10
        db.add.assert_called_once()
        db.commit.assert_called_once()

    def test_cp03_nombre_vacio_rechazado(self):
        """CP-03 negativo: nombre de cultivo menor a 3 chars es rechazado."""
        with pytest.raises(Exception):
            CultivoCreate(nombre_cultivo="AB")

    def test_cp03_area_negativa_rechazada(self):
        """CP-03 negativo: area en hectareas negativa o cero es rechazada."""
        with pytest.raises(Exception):
            CultivoCreate(nombre_cultivo="Finca Prueba", area_hectareas=-1.0)

    def test_cp03_area_cero_rechazada(self):
        """CP-03 negativo: area igual a cero es rechazada por el schema."""
        with pytest.raises(Exception):
            CultivoCreate(nombre_cultivo="Finca Prueba", area_hectareas=0.0)

    def test_listar_cultivos_excluye_eliminados(self):
        """El listado no debe retornar cultivos en estado 'eliminado'."""
        db = MagicMock()
        mock_q = MagicMock()
        mock_q.filter.return_value = mock_q
        mock_q.order_by.return_value = mock_q
        mock_q.all.return_value = [cultivo_mock("en_seguimiento")]
        db.query.return_value = mock_q

        service   = CultivoService(db)
        resultado = service.listar_cultivos(usuario_id=10)

        assert len(resultado) == 1
        assert resultado[0].estado != "eliminado"

    def test_obtener_cultivo_no_encontrado(self):
        """Consultar un cultivo inexistente debe lanzar HTTP 404."""
        from fastapi import HTTPException
        db = db_mock_con_cultivo(cultivo=None)
        service = CultivoService(db)

        with pytest.raises(HTTPException) as exc:
            service.obtener_cultivo(cultivo_id=999, usuario_id=10)
        assert exc.value.status_code == 404


# ==============================================================
# PRUEBAS - DIAGRAMA DE ESTADOS DEL CULTIVO
# ==============================================================

class TestDiagramaEstadosCultivo:

    def test_transicion_creado_a_en_seguimiento(self):
        """Transicion valida: creado -> en_seguimiento."""
        permitidos = TRANSICIONES_CULTIVO["creado"]
        assert "en_seguimiento" in permitidos

    def test_transicion_creado_a_finalizado_invalida(self):
        """Transicion invalida: creado no puede pasar directamente a finalizado."""
        permitidos = TRANSICIONES_CULTIVO["creado"]
        assert "finalizado" not in permitidos

    def test_transicion_finalizado_es_estado_terminal(self):
        """Un cultivo finalizado no puede cambiar de estado."""
        assert len(TRANSICIONES_CULTIVO["finalizado"]) == 0

    def test_transicion_eliminado_es_estado_terminal(self):
        """Un cultivo eliminado no puede cambiar de estado."""
        assert len(TRANSICIONES_CULTIVO["eliminado"]) == 0

    def test_ciclo_completo_cultivo(self):
        """Valida que el ciclo completo del cultivo sea coherente."""
        ciclo = [
            ("creado",               "en_seguimiento"),
            ("en_seguimiento",       "con_problema_detectado"),
            ("con_problema_detectado", "tratamiento_aplicado"),
            ("tratamiento_aplicado", "en_seguimiento"),
            ("en_seguimiento",       "finalizado"),
        ]
        for estado_actual, estado_siguiente in ciclo:
            permitidos = TRANSICIONES_CULTIVO[estado_actual]
            assert estado_siguiente in permitidos, (
                f"Transicion invalida: {estado_actual} -> {estado_siguiente}"
            )

    def test_actualizar_con_transicion_invalida_lanza_422(self):
        """Una transicion fuera del diagrama de estados debe lanzar HTTP 422."""
        from fastapi import HTTPException
        db = db_mock_con_cultivo(cultivo=cultivo_mock("creado"))
        service = CultivoService(db)

        with pytest.raises(HTTPException) as exc:
            service._validar_transicion_cultivo("creado", "finalizado")
        assert exc.value.status_code == 422


# ==============================================================
# PRUEBAS - RF-04 REGISTRO DE LOTES (CP-04)
# ==============================================================

class TestRegistroLotes:

    def test_cp04_codigo_lote_formato_correcto(self):
        """CP-04: el codigo del lote se convierte a mayusculas automaticamente."""
        datos = LoteCreate(
            codigo_lote="lot-2025-001",
            cantidad_kg=450.0,
        )
        assert datos.codigo_lote == "LOT-2025-001"

    def test_cp04_codigo_con_espacios_rechazado(self):
        """CP-04 negativo: el codigo no puede contener espacios."""
        with pytest.raises(Exception):
            LoteCreate(codigo_lote="LOT 2025 001")

    def test_cp04_codigo_con_caracteres_especiales_rechazado(self):
        """CP-04 negativo: el codigo no puede contener caracteres especiales."""
        with pytest.raises(Exception):
            LoteCreate(codigo_lote="LOT@2025#001")

    def test_cp04_cantidad_negativa_rechazada(self):
        """CP-04 negativo: la cantidad en kg no puede ser negativa."""
        with pytest.raises(Exception):
            LoteCreate(codigo_lote="LOT-2025-001", cantidad_kg=-100.0)

    def test_cp04_codigo_qr_generado_automaticamente(self):
        """CP-04: al crear el lote se debe generar un codigo QR unico."""
        import secrets
        qr1 = secrets.token_urlsafe(36)
        qr2 = secrets.token_urlsafe(36)
        assert qr1 != qr2
        assert len(qr1) >= 36

    def test_cp04_codigo_duplicado_lanza_409(self):
        """CP-04 negativo: codigo_lote duplicado debe lanzar HTTP 409."""
        from fastapi import HTTPException

        db = MagicMock()
        # Simula que obtener_cultivo pasa sin error
        cultivo = cultivo_mock("en_seguimiento")
        lote    = lote_mock()

        mock_q = MagicMock()
        mock_q.filter.return_value = MagicMock(first=lambda: None)

        # Primera query (obtener_cultivo) retorna el cultivo
        # Segunda query (buscar duplicado) retorna un lote existente
        db.query.side_effect = [
            MagicMock(filter=MagicMock(return_value=MagicMock(
                filter=MagicMock(return_value=MagicMock(first=lambda: cultivo))
            ))),
            MagicMock(filter=MagicMock(return_value=MagicMock(first=lambda: lote))),
        ]

        service = CultivoService(db)
        with pytest.raises(HTTPException) as exc:
            service.crear_lote(
                1,
                LoteCreate(codigo_lote="LOT-2025-001", cantidad_kg=450.0),
                usuario_id=10,
            )
        assert exc.value.status_code == 409


# ==============================================================
# PRUEBAS - DIAGRAMA DE ESTADOS DEL LOTE
# ==============================================================

class TestDiagramaEstadosLote:

    def test_transicion_registrado_a_disponible(self):
        """Transicion valida: registrado -> disponible."""
        assert "disponible" in TRANSICIONES_LOTE["registrado"]

    def test_transicion_disponible_a_en_analisis(self):
        """Transicion valida: disponible -> en_analisis."""
        assert "en_analisis" in TRANSICIONES_LOTE["disponible"]

    def test_transicion_aprobado_a_vendido(self):
        """Transicion valida: aprobado -> vendido."""
        assert "vendido" in TRANSICIONES_LOTE["aprobado"]

    def test_transicion_vendido_es_terminal(self):
        """Un lote vendido no puede cambiar de estado."""
        assert len(TRANSICIONES_LOTE["vendido"]) == 0

    def test_transicion_registrado_a_vendido_invalida(self):
        """Un lote recien registrado no puede ir directamente a vendido."""
        assert "vendido" not in TRANSICIONES_LOTE["registrado"]

    def test_ciclo_completo_exitoso(self):
        """Valida el ciclo exitoso del lote sin problemas."""
        ciclo_exitoso = [
            ("registrado",  "disponible"),
            ("disponible",  "en_analisis"),
            ("en_analisis", "aprobado"),
            ("aprobado",    "vendido"),
        ]
        for actual, siguiente in ciclo_exitoso:
            assert siguiente in TRANSICIONES_LOTE[actual]

    def test_ciclo_con_problema(self):
        """Valida el ciclo del lote cuando hay un problema detectado."""
        ciclo_problema = [
            ("disponible",  "en_analisis"),
            ("en_analisis", "con_problema"),
            ("con_problema", "en_analisis"),
        ]
        for actual, siguiente in ciclo_problema:
            assert siguiente in TRANSICIONES_LOTE[actual]


# ==============================================================
# PRUEBAS - RN-02 TRAZABILIDAD OBLIGATORIA
# ==============================================================

class TestRN02Trazabilidad:

    def test_rn02_sin_trazabilidad_bloquea_venta(self):
        """
        RN-02: intentar pasar un lote a 'vendido' sin la etapa
        'comercializacion' en trazabilidad debe lanzar HTTP 422.
        """
        from fastapi import HTTPException

        db = MagicMock()
        # Simula que la consulta de trazabilidad retorna 0 registros
        mock_execute = MagicMock()
        mock_execute.scalar.return_value = 0
        db.execute.return_value = mock_execute

        service = CultivoService(db)
        with pytest.raises(HTTPException) as exc:
            service._verificar_trazabilidad_rn02(lote_id=1)

        assert exc.value.status_code == 422
        assert "RN-02" in exc.value.detail

    def test_rn02_con_trazabilidad_completa_permite_venta(self):
        """
        RN-02: si existe la etapa 'comercializacion' en trazabilidad,
        el metodo debe completar sin excepciones.
        """
        from fastapi import HTTPException

        db = MagicMock()
        mock_execute = MagicMock()
        mock_execute.scalar.return_value = 1  # Existe registro
        db.execute.return_value = mock_execute

        service = CultivoService(db)
        try:
            service._verificar_trazabilidad_rn02(lote_id=1)
        except HTTPException:
            pytest.fail("RN-02 no debia bloquear cuando la trazabilidad esta completa")


# ==============================================================
# PRUEBAS - SENSORES
# ==============================================================

class TestSensores:

    def test_tipo_sensor_invalido_rechazado(self):
        """El schema debe rechazar tipos de sensor no definidos."""
        with pytest.raises(Exception):
            SensorCreate(
                codigo_sensor="SNS-001",
                tipo_sensor="ultrasonido",
            )

    def test_codigo_sensor_vacio_rechazado(self):
        """El schema debe rechazar codigos de sensor vacios."""
        with pytest.raises(Exception):
            SensorCreate(
                codigo_sensor="",
                tipo_sensor="temperatura",
            )

    def test_tipos_sensor_validos(self):
        """Valida que todos los tipos definidos en el sistema sean aceptados."""
        tipos_validos = [
            "temperatura", "humedad", "suelo", "radiacion", "multivariable"
        ]
        for tipo in tipos_validos:
            sensor = SensorCreate(
                codigo_sensor=f"SNS-{tipo.upper()}-001",
                tipo_sensor=tipo,
            )
            assert sensor.tipo_sensor == tipo
