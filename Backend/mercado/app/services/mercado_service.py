# ==============================================================
# modulo_06_mercado / app/services/mercado_service.py
# Servicio principal — RF-13 y RF-14
#
# Orquesta:
#   registrar_precio()        Guardar precio de referencia manual
#   sincronizar_ventas_propias() Importar precios desde M05
#   analizar_precios()        Ejecutar análisis estadístico RF-13
#   historial_precios()       Histórico mensual para gráficas
#   analizar_demanda()        Ejecutar análisis de demanda RF-14
#   dashboard_mercado()       Panel consolidado Comercializador
#
# FUENTE DE DATOS INTERNA (M05):
#   El servicio consulta tbl_trazabilidad_lote directamente para
#   obtener precios reales de venta y métricas de demanda.
#   Esto garantiza coherencia y no requiere sincronización manual.
# ==============================================================

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy import func, text
from sqlalchemy.orm import Session

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
from app.core.config import settings
from app.models.mercado import AnalisisDemanda, AnalisisPrecio, PrecioMercado
from app.schemas.mercado import (
    AnalisisDemandaResponse,
    AnalisisPrecioResponse,
    DashboardMercadoResponse,
    DemandaObservacionCreate,
    HistorialPrecioItem,
    PrecioCreate,
    PrecioResponse,
)

logger = logging.getLogger(__name__)


class MercadoService:

    def __init__(self, db: Session):
        self.db = db

    # ----------------------------------------------------------
    # RF-13 — REGISTRO Y ANÁLISIS DE PRECIOS
    # ----------------------------------------------------------

    def registrar_precio(
        self, datos: PrecioCreate, usuario_id: int
    ) -> PrecioResponse:
        """Registra un precio de referencia de mercado."""
        precio = PrecioMercado(
            fuente            = datos.fuente,
            tipo_cafe         = datos.tipo_cafe,
            precio_cop_kg     = datos.precio_cop_kg,
            precio_usd_lb     = datos.precio_usd_lb,
            variedad          = datos.variedad,
            categoria_calidad = datos.categoria_calidad,
            region            = datos.region,
            notas             = datos.notas,
            fecha_precio      = datos.fecha_precio,
            id_usuario        = usuario_id,
        )
        self.db.add(precio)
        self.db.commit()
        self.db.refresh(precio)
        logger.info(f"Precio registrado: {datos.fuente} ${datos.precio_cop_kg}/kg")
        return self._precio_a_response(precio)

    def sincronizar_ventas_propias(self, usuario_id: int) -> int:
        """
        RF-13: importa precios reales de ventas registradas en M05
        (tbl_trazabilidad_lote) que aún no están en tbl_precio_mercado.
        Retorna la cantidad de registros nuevos importados.
        """
        try:
            ventas = self.db.execute(
                text("""
                    SELECT id_lote, codigo_lote, precio_venta_kg,
                           clasificacion_calidad, variedad_cafe,
                           fecha_venta, id_usuario_creador
                    FROM   tbl_trazabilidad_lote
                    WHERE  estado = 'vendido'
                      AND  precio_venta_kg IS NOT NULL
                      AND  id_lote NOT IN (
                               SELECT COALESCE(id_lote_origen, 0)
                               FROM   tbl_precio_mercado
                               WHERE  fuente = 'propio_sistema'
                                 AND  id_lote_origen IS NOT NULL
                           )
                """)
            ).fetchall()
        except Exception as e:
            logger.warning(f"No se pudo consultar tbl_trazabilidad_lote: {e}")
            return 0

        importados = 0
        for v in ventas:
            if v.precio_venta_kg and v.fecha_venta:
                registro = PrecioMercado(
                    fuente            = "propio_sistema",
                    tipo_cafe         = "pergamino_seco",
                    precio_cop_kg     = float(v.precio_venta_kg),
                    categoria_calidad = v.clasificacion_calidad or "todas",
                    variedad          = v.variedad_cafe,
                    notas             = f"Importado automáticamente del lote {v.codigo_lote}",
                    id_lote_origen    = v.id_lote,
                    id_usuario        = usuario_id,
                    fecha_precio      = v.fecha_venta,
                )
                self.db.add(registro)
                importados += 1

        if importados:
            self.db.commit()
            logger.info(f"Sincronizados {importados} precios propios del sistema")
        return importados

    def listar_precios(
        self,
        usuario_id: int,
        fuente:     Optional[str] = None,
        meses:      int           = 6,
    ) -> List[PrecioResponse]:
        """Lista el histórico de precios con filtros opcionales."""
        desde = datetime.now(timezone.utc) - timedelta(days=meses * 30)
        q = self.db.query(PrecioMercado).filter(
            PrecioMercado.fecha_precio >= desde
        )
        if fuente:
            q = q.filter(PrecioMercado.fuente == fuente)
        precios = q.order_by(PrecioMercado.fecha_precio.desc()).all()
        return [self._precio_a_response(p) for p in precios]

    def analizar_precios(
        self,
        usuario_id:    int,
        meses:         int = None,
        tipo_cafe:     str = "pergamino_seco",
        fuente_filtro: str = "todas",
    ) -> AnalisisPrecioResponse:
        """
        RF-13: ejecuta el análisis estadístico de precios del período.

        Pasos:
          1. Sincronizar ventas propias del M05
          2. Obtener precios del período actual
          3. Obtener precios del período anterior (para variación)
          4. Calcular estadísticas: media, min, max, rango
          5. Calcular variación y proyección WMA-3
          6. Clasificar tendencia y generar alertas
          7. Persistir el análisis y retornarlo
        """
        meses_analisis = meses or settings.MESES_HISTORICO_PRECIO

        # Paso 1: sincronizar ventas propias
        self.sincronizar_ventas_propias(usuario_id)

        ahora    = datetime.now(timezone.utc)
        inicio   = ahora - timedelta(days=meses_analisis * 30)
        inicio_a = inicio - timedelta(days=meses_analisis * 30)  # período anterior

        # Paso 2: precios período actual
        q = self.db.query(PrecioMercado).filter(
            PrecioMercado.fecha_precio >= inicio,
            PrecioMercado.tipo_cafe   == tipo_cafe,
        )
        if fuente_filtro and fuente_filtro != "todas":
            q = q.filter(PrecioMercado.fuente == fuente_filtro)
        registros_actuales = q.all()

        if not registros_actuales:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=(
                    f"Sin datos de precios en los últimos {meses_analisis} meses "
                    f"para tipo '{tipo_cafe}'. "
                    "Registre precios de referencia primero."
                ),
            )

        precios_actuales = [float(r.precio_cop_kg) for r in registros_actuales]
        prom, mini, maxi, rango = calcular_estadisticas_precios(precios_actuales)

        # Paso 3: precios período anterior
        q_ant = self.db.query(PrecioMercado).filter(
            PrecioMercado.fecha_precio >= inicio_a,
            PrecioMercado.fecha_precio <  inicio,
            PrecioMercado.tipo_cafe    == tipo_cafe,
        )
        if fuente_filtro and fuente_filtro != "todas":
            q_ant = q_ant.filter(PrecioMercado.fuente == fuente_filtro)
        registros_anteriores = q_ant.all()

        prom_anterior = None
        if registros_anteriores:
            precios_ant   = [float(r.precio_cop_kg) for r in registros_anteriores]
            prom_anterior = sum(precios_ant) / len(precios_ant)

        # Paso 4-5: variación y proyección
        variacion = calcular_variacion_porcentual(prom, prom_anterior)

        # WMA-3: construir serie mensual de promedios para proyectar
        serie_mensual = self._serie_mensual_precios(tipo_cafe, fuente_filtro, 3)
        proyectado    = proyectar_wma3(serie_mensual)

        # Paso 6: tendencia y alertas
        tendencia               = clasificar_tendencia(variacion, rango, prom)
        alerta_activa, msg_alerta = generar_alerta_precio(variacion, prom, tendencia)
        recomendacion, interpretacion = generar_recomendacion_precio(
            tendencia, variacion, prom, settings.PRECIO_BASE_FNC_COP, proyectado
        )

        # Paso 7: persistir
        analisis = AnalisisPrecio(
            periodo_inicio     = inicio,
            periodo_fin        = ahora,
            tipo_cafe          = tipo_cafe,
            fuente_analizada   = fuente_filtro,
            precio_promedio    = prom,
            precio_minimo      = mini,
            precio_maximo      = maxi,
            variacion_pct      = variacion,
            tendencia          = tendencia,
            precio_proyectado  = proyectado,
            alerta_activa      = alerta_activa,
            mensaje_alerta     = msg_alerta,
            recomendacion      = recomendacion,
            num_registros_base = len(registros_actuales),
            id_usuario         = usuario_id,
        )
        self.db.add(analisis)
        self.db.commit()
        self.db.refresh(analisis)

        logger.info(
            f"Análisis de precios generado: tendencia={tendencia} "
            f"prom=${prom} alerta={alerta_activa}"
        )

        return AnalisisPrecioResponse(
            id_analisis        = analisis.id_analisis,
            periodo_inicio     = analisis.periodo_inicio,
            periodo_fin        = analisis.periodo_fin,
            tipo_cafe          = analisis.tipo_cafe,
            fuente_analizada   = analisis.fuente_analizada,
            precio_promedio    = float(analisis.precio_promedio),
            precio_minimo      = float(analisis.precio_minimo),
            precio_maximo      = float(analisis.precio_maximo),
            rango_precios      = rango,
            variacion_pct      = analisis.variacion_pct,
            variacion_label    = formatear_variacion_label(variacion),
            tendencia          = analisis.tendencia,
            tendencia_icono    = ICONOS_TENDENCIA.get(tendencia, "→"),
            precio_proyectado  = float(analisis.precio_proyectado) if analisis.precio_proyectado else None,
            alerta_activa      = analisis.alerta_activa,
            mensaje_alerta     = analisis.mensaje_alerta,
            recomendacion      = analisis.recomendacion,
            num_registros_base = analisis.num_registros_base,
            interpretacion     = interpretacion,
            fecha_analisis     = analisis.fecha_analisis,
        )

    def historial_precios(
        self,
        meses: int = 6,
        tipo_cafe: str = "pergamino_seco",
    ) -> List[HistorialPrecioItem]:
        """
        RF-13: retorna el histórico mensual de precios para gráficas.
        Agrupa por mes y fuente para mostrar comparativas FNC vs propio.
        """
        desde = datetime.now(timezone.utc) - timedelta(days=meses * 30)
        registros = (
            self.db.query(PrecioMercado)
            .filter(
                PrecioMercado.fecha_precio >= desde,
                PrecioMercado.tipo_cafe == tipo_cafe,
            )
            .order_by(PrecioMercado.fecha_precio)
            .all()
        )

        # Agrupar por mes
        meses_dict: dict = {}
        for r in registros:
            clave = r.fecha_precio.strftime("%Y-%m")
            if clave not in meses_dict:
                meses_dict[clave] = {
                    "todos": [], "fnc": [], "propio": []
                }
            meses_dict[clave]["todos"].append(float(r.precio_cop_kg))
            if r.fuente == "fnc":
                meses_dict[clave]["fnc"].append(float(r.precio_cop_kg))
            if r.fuente == "propio_sistema":
                meses_dict[clave]["propio"].append(float(r.precio_cop_kg))

        resultado = []
        for mes_key in sorted(meses_dict.keys()):
            d        = meses_dict[mes_key]
            todos    = d["todos"]
            fnc_list = d["fnc"]
            prp_list = d["propio"]
            resultado.append(HistorialPrecioItem(
                mes           = mes_key,
                precio_prom   = round(sum(todos) / len(todos), 2),
                precio_fnc    = round(sum(fnc_list) / len(fnc_list), 2) if fnc_list else None,
                precio_propio = round(sum(prp_list) / len(prp_list), 2) if prp_list else None,
                num_registros = len(todos),
            ))
        return resultado

    # ----------------------------------------------------------
    # RF-14 — ANÁLISIS DE DEMANDA
    # ----------------------------------------------------------

    def analizar_demanda(
        self,
        usuario_id:     int,
        meses:          int = None,
        observaciones:  Optional[DemandaObservacionCreate] = None,
    ) -> AnalisisDemandaResponse:
        """
        RF-14: ejecuta el análisis de demanda del período.

        Fuente de datos: tbl_trazabilidad_lote (M05)
          - Lotes vendidos en el período
          - Kg totales vendidos
          - Tiempo promedio aprobación → venta
          - Categoría más demandada
          - Comprador más frecuente
          - Destino principal

        Si M05 no está disponible, opera con datos de precios propios
        registrados en tbl_precio_mercado como fallback.
        """
        meses_analisis = meses or settings.MESES_HISTORICO_DEMANDA
        ahora  = datetime.now(timezone.utc)
        inicio = ahora - timedelta(days=meses_analisis * 30)
        inicio_anterior = inicio - timedelta(days=meses_analisis * 30)

        # ── Consultar M05 ───────────────────────────────────────
        metricas = self._consultar_metricas_m05(inicio, ahora)
        metricas_ant = self._consultar_metricas_m05(inicio_anterior, inicio)

        total_lotes   = metricas.get("total_lotes", 0)
        kg_totales    = metricas.get("kg_totales", 0.0)
        kg_prom_lote  = metricas.get("kg_prom", None)
        dias_prom     = metricas.get("dias_prom_venta", None)
        cat_top       = metricas.get("categoria_top", None)
        comprador_top = metricas.get("comprador_top", None)
        destino_top   = metricas.get("destino_top", None)

        total_lotes_ant = metricas_ant.get("total_lotes", 0)
        variacion = calcular_variacion_porcentual(total_lotes, total_lotes_ant)

        # ── Clasificar y generar recomendaciones ────────────────
        nivel = clasificar_nivel_demanda(total_lotes, variacion, dias_prom)
        recomendacion, interpretacion = generar_recomendacion_demanda(
            nivel, total_lotes, kg_totales, dias_prom, cat_top, variacion
        )

        # ── Persistir ──────────────────────────────────────────
        analisis = AnalisisDemanda(
            periodo_inicio          = inicio,
            periodo_fin             = ahora,
            total_lotes_vendidos    = total_lotes,
            kg_totales_vendidos     = kg_totales,
            kg_promedio_por_lote    = kg_prom_lote,
            dias_promedio_venta     = dias_prom,
            categoria_mas_demandada = cat_top,
            comprador_frecuente     = comprador_top,
            destino_principal       = destino_top,
            nivel_demanda           = nivel,
            variacion_demanda_pct   = variacion,
            observaciones_mercado   = observaciones.observaciones_mercado if observaciones else None,
            oportunidades           = observaciones.oportunidades if observaciones else None,
            riesgos                 = observaciones.riesgos if observaciones else None,
            recomendacion           = recomendacion,
            id_usuario              = usuario_id,
        )
        self.db.add(analisis)
        self.db.commit()
        self.db.refresh(analisis)

        logger.info(
            f"Análisis de demanda generado: nivel={nivel} "
            f"lotes={total_lotes} kg={kg_totales:.0f}"
        )

        return AnalisisDemandaResponse(
            id_demanda              = analisis.id_demanda,
            periodo_inicio          = analisis.periodo_inicio,
            periodo_fin             = analisis.periodo_fin,
            total_lotes_vendidos    = analisis.total_lotes_vendidos,
            kg_totales_vendidos     = float(analisis.kg_totales_vendidos),
            kg_promedio_por_lote    = float(analisis.kg_promedio_por_lote) if analisis.kg_promedio_por_lote else None,
            dias_promedio_venta     = analisis.dias_promedio_venta,
            categoria_mas_demandada = analisis.categoria_mas_demandada,
            comprador_frecuente     = analisis.comprador_frecuente,
            destino_principal       = analisis.destino_principal,
            nivel_demanda           = analisis.nivel_demanda,
            nivel_demanda_label     = NIVEL_DEMANDA_LABELS.get(nivel, nivel),
            variacion_demanda_pct   = analisis.variacion_demanda_pct,
            variacion_label         = formatear_variacion_label(variacion),
            observaciones_mercado   = analisis.observaciones_mercado,
            oportunidades           = analisis.oportunidades,
            riesgos                 = analisis.riesgos,
            recomendacion           = analisis.recomendacion,
            interpretacion          = interpretacion,
            fecha_analisis          = analisis.fecha_analisis,
        )

    # ----------------------------------------------------------
    # DASHBOARD CONSOLIDADO
    # ----------------------------------------------------------

    def dashboard_mercado(self, usuario_id: int) -> DashboardMercadoResponse:
        """
        Panel consolidado para el Comercializador.
        Combina precio actual, stock disponible, demanda del mes
        y proyección para apoyar decisiones comerciales (RF-13 + RF-14).
        """
        ahora  = datetime.now(timezone.utc)
        inicio = ahora - timedelta(days=30)

        # Sincronizar ventas propias antes del dashboard
        self.sincronizar_ventas_propias(usuario_id)

        # Último precio propio registrado
        ultimo_precio = (
            self.db.query(PrecioMercado)
            .filter(PrecioMercado.fuente == "propio_sistema")
            .order_by(PrecioMercado.fecha_precio.desc())
            .first()
        )
        precio_actual = float(ultimo_precio.precio_cop_kg) if ultimo_precio else None

        # Último precio FNC registrado
        ultimo_fnc = (
            self.db.query(PrecioMercado)
            .filter(PrecioMercado.fuente == "fnc")
            .order_by(PrecioMercado.fecha_precio.desc())
            .first()
        )
        precio_fnc = float(ultimo_fnc.precio_cop_kg) if ultimo_fnc else settings.PRECIO_BASE_FNC_COP

        diferencial = None
        if precio_actual and precio_fnc:
            diferencial = round((precio_actual - precio_fnc) / precio_fnc * 100, 1)

        # Último análisis de precio
        ultimo_analisis = (
            self.db.query(AnalisisPrecio)
            .order_by(AnalisisPrecio.fecha_analisis.desc())
            .first()
        )
        tendencia_actual     = ultimo_analisis.tendencia if ultimo_analisis else None
        alerta_precio        = ultimo_analisis.alerta_activa if ultimo_analisis else False
        msg_alerta_precio    = ultimo_analisis.mensaje_alerta if ultimo_analisis else None
        precio_proyectado    = (
            float(ultimo_analisis.precio_proyectado)
            if ultimo_analisis and ultimo_analisis.precio_proyectado else None
        )

        # Lotes y kg disponibles (M05)
        lotes_disp, kg_disp = self._lotes_disponibles()

        # Ventas del mes en curso (M05)
        metricas_mes = self._consultar_metricas_m05(inicio, ahora)
        lotes_mes    = metricas_mes.get("total_lotes", 0)
        kg_mes       = metricas_mes.get("kg_totales", 0.0)

        # Nivel de demanda del último análisis
        ultimo_demanda = (
            self.db.query(AnalisisDemanda)
            .order_by(AnalisisDemanda.fecha_analisis.desc())
            .first()
        )
        nivel_demanda = (
            NIVEL_DEMANDA_LABELS.get(ultimo_demanda.nivel_demanda)
            if ultimo_demanda else None
        )

        # Recomendación combinada
        if alerta_precio and tendencia_actual == "baja":
            reco = (
                "Precios en baja y alerta activa. Evalúe si tiene urgencia de venta. "
                "Mantenga comunicación con sus compradores habituales."
            )
        elif lotes_disp > 0 and tendencia_actual == "alza":
            reco = (
                f"Tiene {lotes_disp} lote(s) aprobado(s) disponibles y los precios están al alza. "
                "Buen momento para iniciar negociaciones de venta."
            )
        elif lotes_disp == 0:
            reco = "Sin lotes aprobados disponibles. Enfóquese en preparar nuevos lotes."
        else:
            reco = (
                "Condiciones estables. Revise los análisis de precio y demanda "
                "para tomar decisiones informadas."
            )

        # Alertas activas
        alertas = []
        if alerta_precio and msg_alerta_precio:
            alertas.append(msg_alerta_precio)
        if lotes_disp == 0:
            alertas.append("Sin stock aprobado disponible para venta.")
        if ultimo_demanda and ultimo_demanda.nivel_demanda == "baja":
            alertas.append("La demanda del período es baja. Diversifique canales de venta.")

        return DashboardMercadoResponse(
            precio_actual_cop      = precio_actual,
            precio_fnc_referencia  = precio_fnc,
            diferencial_fnc_pct    = diferencial,
            tendencia_precio       = tendencia_actual,
            alerta_precio          = alerta_precio,
            mensaje_alerta_precio  = msg_alerta_precio,
            lotes_disponibles      = lotes_disp,
            kg_disponibles         = kg_disp,
            total_vendido_mes      = lotes_mes,
            kg_vendidos_mes        = kg_mes,
            nivel_demanda_actual   = nivel_demanda,
            precio_proyectado_mes  = precio_proyectado,
            recomendacion_comercial= reco,
            alertas                = alertas,
            fecha_actualizacion    = ahora,
        )

    # ----------------------------------------------------------
    # HELPERS PRIVADOS
    # ----------------------------------------------------------

    def _consultar_metricas_m05(
        self, inicio: datetime, fin: datetime
    ) -> dict:
        """
        Consulta métricas de ventas de M05 para el período dado.
        Retorna dict vacío si tbl_trazabilidad_lote no está disponible.
        """
        try:
            r = self.db.execute(
                text("""
                    SELECT
                        COUNT(*)                          AS total_lotes,
                        COALESCE(SUM(kg_pergamino_seco), 0) AS kg_totales,
                        AVG(kg_pergamino_seco)            AS kg_prom,
                        AVG(DATEDIFF(fecha_venta,
                            COALESCE(fecha_fin_secado, fecha_creacion)))
                                                          AS dias_prom_venta
                    FROM tbl_trazabilidad_lote
                    WHERE estado = 'vendido'
                      AND fecha_venta BETWEEN :ini AND :fin
                """),
                {"ini": inicio, "fin": fin},
            ).fetchone()

            top_cat = self.db.execute(
                text("""
                    SELECT clasificacion_calidad, COUNT(*) AS cnt
                    FROM   tbl_trazabilidad_lote
                    WHERE  estado = 'vendido'
                      AND  fecha_venta BETWEEN :ini AND :fin
                    GROUP BY clasificacion_calidad
                    ORDER BY cnt DESC LIMIT 1
                """),
                {"ini": inicio, "fin": fin},
            ).fetchone()

            top_comp = self.db.execute(
                text("""
                    SELECT comprador, COUNT(*) AS cnt
                    FROM   tbl_trazabilidad_lote
                    WHERE  estado = 'vendido'
                      AND  comprador IS NOT NULL
                      AND  fecha_venta BETWEEN :ini AND :fin
                    GROUP BY comprador
                    ORDER BY cnt DESC LIMIT 1
                """),
                {"ini": inicio, "fin": fin},
            ).fetchone()

            top_dest = self.db.execute(
                text("""
                    SELECT destino_exportacion, COUNT(*) AS cnt
                    FROM   tbl_trazabilidad_lote
                    WHERE  estado = 'vendido'
                      AND  destino_exportacion IS NOT NULL
                      AND  fecha_venta BETWEEN :ini AND :fin
                    GROUP BY destino_exportacion
                    ORDER BY cnt DESC LIMIT 1
                """),
                {"ini": inicio, "fin": fin},
            ).fetchone()

            return {
                "total_lotes":      int(r.total_lotes) if r else 0,
                "kg_totales":       float(r.kg_totales) if r and r.kg_totales else 0.0,
                "kg_prom":          float(r.kg_prom) if r and r.kg_prom else None,
                "dias_prom_venta":  float(r.dias_prom_venta) if r and r.dias_prom_venta else None,
                "categoria_top":    top_cat.clasificacion_calidad if top_cat else None,
                "comprador_top":    top_comp.comprador if top_comp else None,
                "destino_top":      top_dest.destino_exportacion if top_dest else None,
            }
        except Exception as e:
            logger.warning(f"M05 no disponible para métricas de demanda: {e}")
            return {}

    def _lotes_disponibles(self):
        """Retorna (total_lotes, kg_totales) de lotes en estado 'aprobado'."""
        try:
            r = self.db.execute(
                text("""
                    SELECT COUNT(*) AS lotes,
                           COALESCE(SUM(kg_pergamino_seco), 0) AS kg
                    FROM   tbl_trazabilidad_lote
                    WHERE  estado = 'aprobado'
                """)
            ).fetchone()
            return int(r.lotes), float(r.kg)
        except Exception:
            return 0, 0.0

    def _serie_mensual_precios(
        self, tipo_cafe: str, fuente: str, num_meses: int
    ) -> List[float]:
        """Retorna lista de promedios mensuales para proyección WMA-3."""
        desde = datetime.now(timezone.utc) - timedelta(days=num_meses * 30)
        q = self.db.query(PrecioMercado).filter(
            PrecioMercado.fecha_precio >= desde,
            PrecioMercado.tipo_cafe == tipo_cafe,
        )
        if fuente and fuente != "todas":
            q = q.filter(PrecioMercado.fuente == fuente)

        registros = q.order_by(PrecioMercado.fecha_precio).all()
        if not registros:
            return []

        meses_dict: dict = {}
        for r in registros:
            clave = r.fecha_precio.strftime("%Y-%m")
            meses_dict.setdefault(clave, []).append(float(r.precio_cop_kg))

        return [
            round(sum(v) / len(v), 2)
            for v in [meses_dict[k] for k in sorted(meses_dict.keys())]
        ]

    def _precio_a_response(self, p: PrecioMercado) -> PrecioResponse:
        return PrecioResponse(
            id_precio         = p.id_precio,
            fuente            = p.fuente,
            tipo_cafe         = p.tipo_cafe,
            precio_cop_kg     = float(p.precio_cop_kg),
            precio_usd_lb     = float(p.precio_usd_lb) if p.precio_usd_lb else None,
            variedad          = p.variedad,
            categoria_calidad = p.categoria_calidad,
            region            = p.region,
            notas             = p.notas,
            id_lote_origen    = p.id_lote_origen,
            fecha_precio      = p.fecha_precio,
            fecha_registro    = p.fecha_registro,
        )
