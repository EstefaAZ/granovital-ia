# ==============================================================
# modulo_03_monitoreo / tests/test_monitoreo.py
# Pruebas unitarias alineadas con el Test Plan del proyecto
#
# Cobertura:
#   RF-03  Monitoreo ambiental - registro y alertas
#   RF-04  Monitoreo de suelo  - registro, pH e interpretacion
#   RN-03  Validacion de datos actualizados para modulo de IA
#   RNF-09 Ingesta desde sensores IoT (mqtt_client)
#   RNF-10 Ingreso manual en zonas sin conectividad
#
# Metodologia: mocks de SQLAlchemy Session para pruebas
# unitarias puras sin necesidad de base de datos real.
# ==============================================================

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch

from app.schemas.monitoreo import (
    MonitoreoAmbientalCreate,
    MonitoreoSueloCreate,
)
from app.services.monitoreo_service import (
    MonitoreoService,
    RANGOS_AMBIENTAL,
    RANGOS_SUELO,
)


# ==============================================================
# FIXTURES
# ==============================================================

def registro_ambiental_mock(
    temperatura:      float = 22.0,
    humedad_relativa: float = 78.0,
    horas_atras:      float = 0.5,
    cultivo_id:       int   = 1,
):
    r = MagicMock()
    r.id_monitoreo     = 1
    r.temperatura      = temperatura
    r.humedad_relativa = humedad_relativa
    r.precipitacion_mm = 8.0
    r.radiacion_solar  = 420.0
    r.velocidad_viento = 7.5
    r.origen_dato      = "manual"
    r.id_sensor        = None
    r.observaciones    = None
    r.id_cultivo       = cultivo_id
    r.fecha_registro   = datetime.now(timezone.utc) - timedelta(hours=horas_atras)
    return r


def registro_suelo_mock(
    ph:           float = 6.2,
    humedad:      float = 55.0,
    nitrogeno:    float = 28.0,
    fosforo:      float = 18.0,
    potasio:      float = 22.0,
    horas_atras:  float = 1.0,
    cultivo_id:   int   = 1,
):
    r = MagicMock()
    r.id_monitoreo_suelo = 1
    r.ph               = ph
    r.humedad_suelo    = humedad
    r.nitrogeno        = nitrogeno
    r.fosforo          = fosforo
    r.potasio          = potasio
    r.materia_organica = 3.8
    r.conductividad_ec = 0.45
    r.origen_dato      = "laboratorio"
    r.id_sensor        = None
    r.observaciones    = None
    r.id_cultivo       = cultivo_id
    r.fecha_registro   = datetime.now(timezone.utc) - timedelta(hours=horas_atras)
    return r


def db_base():
    """Base de datos mock con acceso al cultivo verificado."""
    db = MagicMock()
    # _verificar_acceso_cultivo usa db.execute().fetchone()
    resultado_acceso = MagicMock()
    db.execute.return_value.fetchone.return_value = resultado_acceso
    return db


def servicio_con_db(db=None):
    return MonitoreoService(db or db_base())


# ==============================================================
# PRUEBAS - VALIDACIONES PYDANTIC AMBIENTAL
# ==============================================================

class TestValidacionesAmbiental:

    def test_temperatura_fuera_de_rango_superior(self):
        """El schema debe rechazar temperaturas superiores a 55 C."""
        with pytest.raises(Exception):
            MonitoreoAmbientalCreate(temperatura=60.0)

    def test_temperatura_fuera_de_rango_inferior(self):
        """El schema debe rechazar temperaturas inferiores a -10 C."""
        with pytest.raises(Exception):
            MonitoreoAmbientalCreate(temperatura=-15.0)

    def test_humedad_mayor_a_100_rechazada(self):
        """El schema debe rechazar humedad relativa mayor a 100%."""
        with pytest.raises(Exception):
            MonitoreoAmbientalCreate(humedad_relativa=110.0)

    def test_humedad_negativa_rechazada(self):
        """El schema debe rechazar humedad relativa negativa."""
        with pytest.raises(Exception):
            MonitoreoAmbientalCreate(humedad_relativa=-5.0)

    def test_precipitacion_negativa_rechazada(self):
        """El schema debe rechazar precipitacion negativa."""
        with pytest.raises(Exception):
            MonitoreoAmbientalCreate(precipitacion_mm=-1.0)

    def test_origen_invalido_rechazado(self):
        """El schema debe rechazar origenes no definidos en el sistema."""
        with pytest.raises(Exception):
            MonitoreoAmbientalCreate(
                temperatura=22.0,
                origen_dato="bluetooth"
            )

    def test_origen_manual_valido(self):
        """El origen 'manual' debe ser aceptado (RNF-10)."""
        dato = MonitoreoAmbientalCreate(
            temperatura=21.0,
            origen_dato="manual"
        )
        assert dato.origen_dato == "manual"

    def test_origen_sensor_iot_valido(self):
        """El origen 'sensor_iot' debe ser aceptado (RNF-09)."""
        dato = MonitoreoAmbientalCreate(
            temperatura=23.0,
            origen_dato="sensor_iot"
        )
        assert dato.origen_dato == "sensor_iot"

    def test_temperatura_en_rango_valida(self):
        """Temperatura dentro del rango permitido debe aceptarse."""
        dato = MonitoreoAmbientalCreate(temperatura=22.5)
        assert dato.temperatura == 22.5

    def test_multiples_variables_en_un_registro(self):
        """Se deben aceptar multiples variables en un solo registro."""
        dato = MonitoreoAmbientalCreate(
            temperatura=22.0,
            humedad_relativa=75.0,
            precipitacion_mm=10.0,
            radiacion_solar=400.0,
            velocidad_viento=8.0,
        )
        assert dato.temperatura      == 22.0
        assert dato.humedad_relativa == 75.0
        assert dato.precipitacion_mm == 10.0


# ==============================================================
# PRUEBAS - VALIDACIONES PYDANTIC SUELO
# ==============================================================

class TestValidacionesSuelo:

    def test_ph_mayor_a_14_rechazado(self):
        """El schema debe rechazar pH mayor a 14."""
        with pytest.raises(Exception):
            MonitoreoSueloCreate(ph=15.0)

    def test_ph_negativo_rechazado(self):
        """El schema debe rechazar pH negativo."""
        with pytest.raises(Exception):
            MonitoreoSueloCreate(ph=-1.0)

    def test_humedad_mayor_a_100_rechazada(self):
        """El schema debe rechazar humedad de suelo mayor a 100%."""
        with pytest.raises(Exception):
            MonitoreoSueloCreate(humedad_suelo=105.0)

    def test_nitrogeno_negativo_rechazado(self):
        """El schema debe rechazar nitrogeno negativo."""
        with pytest.raises(Exception):
            MonitoreoSueloCreate(nitrogeno=-5.0)

    def test_origen_laboratorio_valido(self):
        """El origen 'laboratorio' debe ser aceptado."""
        dato = MonitoreoSueloCreate(ph=6.2, origen_dato="laboratorio")
        assert dato.origen_dato == "laboratorio"

    def test_ph_optimo_aceptado(self):
        """pH en rango optimo para cafe (5.5-6.5) debe aceptarse."""
        dato = MonitoreoSueloCreate(ph=6.0)
        assert dato.ph == 6.0

    def test_ph_extremo_pero_en_escala(self):
        """pH extremo (0 o 14) debe aceptarse pues esta en escala."""
        dato1 = MonitoreoSueloCreate(ph=0.0)
        dato2 = MonitoreoSueloCreate(ph=14.0)
        assert dato1.ph == 0.0
        assert dato2.ph == 14.0


# ==============================================================
# PRUEBAS - ALERTAS AGRONOMICAS (RF-03)
# ==============================================================

class TestAlertasAgronomicas:

    def setup_method(self):
        self.service = servicio_con_db()

    def test_temperatura_baja_genera_alerta(self):
        """Temperatura por debajo de 14 C debe generar alerta critica."""
        datos = MonitoreoAmbientalCreate(temperatura=12.0)
        alerta_t, _ = self.service._calcular_alertas_ambientales(datos)
        assert alerta_t is not None
        assert "frio" in alerta_t.lower() or "baja" in alerta_t.lower()

    def test_temperatura_alta_genera_alerta(self):
        """Temperatura por encima de 30 C debe generar alerta."""
        datos = MonitoreoAmbientalCreate(temperatura=35.0)
        alerta_t, _ = self.service._calcular_alertas_ambientales(datos)
        assert alerta_t is not None
        assert "alta" in alerta_t.lower() or "estres" in alerta_t.lower()

    def test_temperatura_optima_sin_alerta(self):
        """Temperatura en rango optimo (18-24 C) no debe generar alerta."""
        datos = MonitoreoAmbientalCreate(temperatura=21.0)
        alerta_t, _ = self.service._calcular_alertas_ambientales(datos)
        assert alerta_t is None

    def test_humedad_muy_baja_genera_alerta(self):
        """Humedad por debajo de 55% debe alertar sobre estres hidrico."""
        datos = MonitoreoAmbientalCreate(humedad_relativa=45.0)
        _, alerta_h = self.service._calcular_alertas_ambientales(datos)
        assert alerta_h is not None
        assert "riego" in alerta_h.lower() or "baja" in alerta_h.lower()

    def test_humedad_muy_alta_genera_alerta_roya(self):
        """Humedad mayor a 95% debe alertar sobre riesgo de Roya."""
        datos = MonitoreoAmbientalCreate(humedad_relativa=97.0)
        _, alerta_h = self.service._calcular_alertas_ambientales(datos)
        assert alerta_h is not None
        assert "roya" in alerta_h.lower() or "hongo" in alerta_h.lower() or "alta" in alerta_h.lower()

    def test_humedad_optima_sin_alerta(self):
        """Humedad en rango optimo (70-90%) no debe generar alerta."""
        datos = MonitoreoAmbientalCreate(humedad_relativa=80.0)
        _, alerta_h = self.service._calcular_alertas_ambientales(datos)
        assert alerta_h is None

    def test_sin_variables_no_hay_alerta(self):
        """Datos sin variables no deben generar alertas."""
        datos = MonitoreoAmbientalCreate(precipitacion_mm=5.0)
        alerta_t, alerta_h = self.service._calcular_alertas_ambientales(datos)
        assert alerta_t is None
        assert alerta_h is None


# ==============================================================
# PRUEBAS - INTERPRETACION DE pH (RF-04)
# ==============================================================

class TestInterpretacionPH:

    def setup_method(self):
        self.service = servicio_con_db()

    def test_ph_muy_acido_requiere_encalado_urgente(self):
        """pH menor a 4.5 debe recomendar encalado urgente."""
        resultado = self.service._interpretar_ph(4.0)
        assert resultado is not None
        assert "encalado" in resultado.lower() or "urgente" in resultado.lower()

    def test_ph_optimo_mensaje_positivo(self):
        """pH entre 5.5 y 6.5 debe indicar condicion ideal."""
        resultado = self.service._interpretar_ph(6.0)
        assert resultado is not None
        assert "optimo" in resultado.lower() or "ideal" in resultado.lower()

    def test_ph_alcalino_sugiere_azufre(self):
        """pH mayor a 7.5 debe sugerir azufre agricola."""
        resultado = self.service._interpretar_ph(8.0)
        assert resultado is not None
        assert "azufre" in resultado.lower() or "alcalino" in resultado.lower()

    def test_ph_ligeramente_acido_advierte(self):
        """pH entre 4.5 y 5.5 debe aconsejar encalado moderado."""
        resultado = self.service._interpretar_ph(5.0)
        assert resultado is not None
        assert "encalado" in resultado.lower() or "acido" in resultado.lower()

    def test_ph_none_retorna_none(self):
        """pH no informado (None) debe retornar None sin error."""
        assert self.service._interpretar_ph(None) is None

    def test_ph_limites_optimo(self):
        """Los extremos del rango optimo (5.5 y 6.5) son aceptables."""
        r1 = self.service._interpretar_ph(5.5)
        r2 = self.service._interpretar_ph(6.5)
        assert r1 is not None
        assert r2 is not None


# ==============================================================
# PRUEBAS - ALERTAS NPK (RF-04)
# ==============================================================

class TestAlertasNutrientes:

    def setup_method(self):
        self.service = servicio_con_db()

    def test_nitrogeno_bajo_genera_alerta(self):
        """Nitrogeno menor a 20 mg/kg debe generar alerta de deficiencia."""
        datos = MonitoreoSueloCreate(nitrogeno=10.0, origen_dato="manual")
        alerta = self.service._calcular_alerta_nutrientes(datos)
        assert alerta is not None
        assert "N" in alerta or "nitrogeno" in alerta.lower()

    def test_fosforo_bajo_genera_alerta(self):
        """Fosforo menor a 15 mg/kg debe generar alerta."""
        datos = MonitoreoSueloCreate(fosforo=8.0, origen_dato="manual")
        alerta = self.service._calcular_alerta_nutrientes(datos)
        assert alerta is not None
        assert "P" in alerta or "fosforo" in alerta.lower()

    def test_potasio_bajo_genera_alerta(self):
        """Potasio menor a 20 mg/kg debe generar alerta."""
        datos = MonitoreoSueloCreate(potasio=12.0, origen_dato="manual")
        alerta = self.service._calcular_alerta_nutrientes(datos)
        assert alerta is not None
        assert "K" in alerta or "potasio" in alerta.lower()

    def test_deficiencia_multiple_npk(self):
        """Deficiencia simultanea en N, P y K debe incluir los tres."""
        datos = MonitoreoSueloCreate(
            nitrogeno=5.0, fosforo=5.0, potasio=5.0,
            origen_dato="manual"
        )
        alerta = self.service._calcular_alerta_nutrientes(datos)
        assert alerta is not None
        assert "N" in alerta
        assert "P" in alerta
        assert "K" in alerta

    def test_nutrientes_optimos_sin_alerta(self):
        """Nutrientes sobre los minimos no deben generar alerta."""
        datos = MonitoreoSueloCreate(
            nitrogeno=30.0, fosforo=25.0, potasio=30.0,
            origen_dato="manual"
        )
        alerta = self.service._calcular_alerta_nutrientes(datos)
        assert alerta is None

    def test_nutrientes_none_sin_alerta(self):
        """Nutrientes no informados no deben generar alerta."""
        datos = MonitoreoSueloCreate(ph=6.0, origen_dato="manual")
        alerta = self.service._calcular_alerta_nutrientes(datos)
        assert alerta is None


# ==============================================================
# PRUEBAS - RN-03 VALIDACION DE DATOS
# ==============================================================

class TestRN03ValidezDatos:

    def _db_con_registros(
        self,
        horas_amb: float = 1.0,
        horas_sue: float = 2.0,
    ):
        """DB mock con lecturas a N horas atras."""
        db = MagicMock()
        # _verificar_acceso_cultivo
        db.execute.return_value.fetchone.return_value = MagicMock()

        amb = registro_ambiental_mock(horas_atras=horas_amb)
        sue = registro_suelo_mock(horas_atras=horas_sue)

        contador_query = [0]

        def query_side_effect(modelo):
            q = MagicMock()
            f = MagicMock()
            ob = MagicMock()

            from app.models.monitoreo import MonitoreoAmbiental, MonitoreoSuelo
            if modelo is MonitoreoAmbiental:
                ob.first.return_value = amb
            elif modelo is MonitoreoSuelo:
                ob.first.return_value = sue

            ob.limit.return_value = ob
            ob.all.return_value = [amb if modelo is MonitoreoAmbiental else sue]
            f.order_by.return_value = ob
            q.filter.return_value = f
            return q

        db.query.side_effect = query_side_effect
        return db

    def test_datos_recientes_ambos_validos(self):
        """Lecturas de 1 hora atras deben resultar en ambos_validos=True."""
        db      = self._db_con_registros(horas_amb=1.0, horas_sue=2.0)
        service = MonitoreoService(db)
        result  = service.verificar_validez_rn03(cultivo_id=1, usuario_id=10)
        assert result.ambiental_valido is True
        assert result.suelo_valido     is True
        assert result.ambos_validos    is True

    def test_ambiental_desactualizado_ambos_invalidos(self):
        """
        Lectura ambiental de 30 horas atras debe hacer
        ambos_validos=False aunque el suelo este actualizado.
        """
        db      = self._db_con_registros(horas_amb=30.0, horas_sue=1.0)
        service = MonitoreoService(db)
        result  = service.verificar_validez_rn03(cultivo_id=1, usuario_id=10)
        assert result.ambiental_valido is False
        assert result.ambos_validos    is False

    def test_suelo_desactualizado_ambos_invalidos(self):
        """
        Lectura de suelo de 25 horas atras debe hacer
        ambos_validos=False aunque el ambiental este actualizado.
        """
        db      = self._db_con_registros(horas_amb=1.0, horas_sue=25.0)
        service = MonitoreoService(db)
        result  = service.verificar_validez_rn03(cultivo_id=1, usuario_id=10)
        assert result.suelo_valido  is False
        assert result.ambos_validos is False

    def test_ambos_desactualizados_mensaje_claro(self):
        """Cuando ambos datos caducan el mensaje debe ser explicativo."""
        db      = self._db_con_registros(horas_amb=48.0, horas_sue=48.0)
        service = MonitoreoService(db)
        result  = service.verificar_validez_rn03(cultivo_id=1, usuario_id=10)
        assert result.ambos_validos is False
        assert "registre" in result.mensaje.lower() or "24" in result.mensaje

    def test_horas_calculadas_correctamente(self):
        """Las horas desde la ultima lectura deben calcularse correctamente."""
        db      = self._db_con_registros(horas_amb=5.0, horas_sue=10.0)
        service = MonitoreoService(db)
        result  = service.verificar_validez_rn03(cultivo_id=1, usuario_id=10)
        assert result.horas_desde_ambiental is not None
        assert 4.5 <= result.horas_desde_ambiental <= 5.5
        assert result.horas_desde_suelo is not None
        assert 9.5 <= result.horas_desde_suelo <= 10.5

    def test_horas_limite_correcto(self):
        """El campo horas_limite debe coincidir con la configuracion."""
        from app.core.config import settings
        db      = self._db_con_registros()
        service = MonitoreoService(db)
        result  = service.verificar_validez_rn03(cultivo_id=1, usuario_id=10)
        assert result.horas_limite == settings.HORAS_DATOS_VALIDOS


# ==============================================================
# PRUEBAS - MQTT CLIENT (RNF-09)
# ==============================================================

class TestMQTTClient:

    def test_extraer_cultivo_ambiental_del_topic(self):
        """El parser debe extraer cultivo_id y tipo del topic."""
        from mqtt_client import _extraer_cultivo_y_tipo
        resultado = _extraer_cultivo_y_tipo("granovital/cultivo/5/ambiental")
        assert resultado == (5, "ambiental")

    def test_extraer_cultivo_suelo_del_topic(self):
        """El parser debe extraer correctamente el tipo 'suelo'."""
        from mqtt_client import _extraer_cultivo_y_tipo
        resultado = _extraer_cultivo_y_tipo("granovital/cultivo/12/suelo")
        assert resultado == (12, "suelo")

    def test_topic_invalido_retorna_none(self):
        """Topics que no cumplen el patron deben retornar None."""
        from mqtt_client import _extraer_cultivo_y_tipo
        assert _extraer_cultivo_y_tipo("otro/topico/invalido") is None
        assert _extraer_cultivo_y_tipo("granovital/cultivo/abc/ambiental") is None

    def test_payload_ambiental_valido_persiste(self):
        """Un payload JSON valido debe persistir una lectura ambiental."""
        from mqtt_client import _persistir_ambiental
        db = MagicMock()
        payload = {"temperatura": 22.5, "humedad_relativa": 78.0, "id_sensor": 3}
        _persistir_ambiental(db, cultivo_id=1, payload=payload)
        db.add.assert_called_once()
        db.commit.assert_called_once()

    def test_payload_suelo_valido_persiste(self):
        """Un payload JSON valido debe persistir una lectura de suelo."""
        from mqtt_client import _persistir_suelo
        db = MagicMock()
        payload = {"ph": 6.2, "humedad_suelo": 55.0, "nitrogeno": 28.0}
        _persistir_suelo(db, cultivo_id=1, payload=payload)
        db.add.assert_called_once()
        db.commit.assert_called_once()

    def test_payload_ambiental_sin_campos_validos_no_persiste(self):
        """Payload sin campos permitidos no debe guardar nada."""
        from mqtt_client import _persistir_ambiental
        db = MagicMock()
        payload = {"campo_desconocido": 99.9}
        _persistir_ambiental(db, cultivo_id=1, payload=payload)
        db.add.assert_not_called()

    def test_payload_suelo_sin_campos_validos_no_persiste(self):
        """Payload de suelo sin campos permitidos no debe guardar nada."""
        from mqtt_client import _persistir_suelo
        db = MagicMock()
        payload = {"campo_extra": "valor"}
        _persistir_suelo(db, cultivo_id=1, payload=payload)
        db.add.assert_not_called()


# ==============================================================
# PRUEBAS - VALIDACION DE AL MENOS UNA VARIABLE
# ==============================================================

class TestValidacionVariableObligatoria:

    def setup_method(self):
        self.service = servicio_con_db()

    def test_ambiental_sin_variables_lanza_422(self):
        """Registro ambiental con todos los campos en None debe lanzar 422."""
        from fastapi import HTTPException
        datos = MonitoreoAmbientalCreate(origen_dato="manual")
        with pytest.raises(HTTPException) as exc:
            self.service._validar_al_menos_una_variable_ambiental(datos)
        assert exc.value.status_code == 422

    def test_suelo_sin_variables_lanza_422(self):
        """Registro de suelo con todos los campos en None debe lanzar 422."""
        from fastapi import HTTPException
        datos = MonitoreoSueloCreate(origen_dato="manual")
        with pytest.raises(HTTPException) as exc:
            self.service._validar_al_menos_una_variable_suelo(datos)
        assert exc.value.status_code == 422

    def test_ambiental_con_solo_precipitacion_es_valido(self):
        """Registro con solo precipitacion informada debe pasar validacion."""
        from fastapi import HTTPException
        datos = MonitoreoAmbientalCreate(precipitacion_mm=15.0)
        try:
            self.service._validar_al_menos_una_variable_ambiental(datos)
        except HTTPException:
            pytest.fail("No debia lanzar excepcion con una variable informada")

    def test_suelo_con_solo_ph_es_valido(self):
        """Registro con solo pH informado debe pasar validacion."""
        from fastapi import HTTPException
        datos = MonitoreoSueloCreate(ph=6.0)
        try:
            self.service._validar_al_menos_una_variable_suelo(datos)
        except HTTPException:
            pytest.fail("No debia lanzar excepcion con una variable informada")
