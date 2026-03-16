# ==============================================================
# modulo_07_reportes / app/services/reportes_service.py
# Servicio principal — RF-18
#
# Implementa el diagrama de estados del documento oficial:
#   Solicitado → Generando → Disponible → Descargado
#                          ↘ Error
#
# Tipos de reporte soportados (RF-18: "sistema y cultivo"):
#   general       Resumen ejecutivo de todo el sistema
#   cultivos      Registro de fincas, lotes y producción
#   trazabilidad  Cadena lote cosecha→secado→clasificación→venta
#   fitosanitario Análisis IA de enfermedades y plagas
#   ambiental     Lecturas de sensores ambientales y de suelo
#   mercado       Precios y análisis de demanda
#   usuarios      Usuarios del sistema y roles
#
# AUDITORÍA:
#   registrar_evento_auditoria() es el punto de entrada para que
#   cualquier módulo del sistema registre un evento de auditoría.
#   La tabla tbl_auditoria es append-only (RNF-05).
# ==============================================================

import json
import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.generadores.generador_pdf import generar_pdf
from app.models.reportes import RegistroAuditoria, Reporte
from app.schemas.reportes import (
    AuditoriaCreate,
    AuditoriaResponse,
    AuditoriaFiltros,
    ReporteListItem,
    ReporteResponse,
    ReporteSolicitud,
    ResumenSistemaResponse,
)

logger = logging.getLogger(__name__)

ESTADOS_LABEL = {
    "solicitado":  "📋 Solicitado",
    "generando":   "⏳ Generando...",
    "disponible":  "✅ Disponible",
    "error":       "❌ Error",
    "descargado":  "📥 Descargado",
}


class ReportesService:

    def __init__(self, db: Session):
        self.db = db

    # ----------------------------------------------------------
    # RF-18 — GENERACIÓN DE REPORTES
    # ----------------------------------------------------------

    def solicitar_reporte(
        self,
        solicitud:      ReporteSolicitud,
        usuario_id:     int,
        nombre_usuario: str = "Administrador",
    ) -> ReporteResponse:
        """
        Genera un reporte siguiendo el diagrama de estados oficial:
        solicitado → generando → disponible (o error).

        La generación es síncrona para cumplir RNF-01 (< 5 s)
        en los volúmenes de datos esperados de una finca cafetera.
        """
        nombre_auto = solicitud.nombre or (
            f"Reporte {solicitud.tipo_reporte.title()} "
            f"{datetime.utcnow().strftime('%d/%m/%Y %H:%M')}"
        )
        params_json = json.dumps({
            "fecha_inicio": solicitud.fecha_inicio.isoformat() if solicitud.fecha_inicio else None,
            "fecha_fin":    solicitud.fecha_fin.isoformat()    if solicitud.fecha_fin    else None,
        })

        # ── Estado: SOLICITADO ──────────────────────────────────
        reporte = Reporte(
            tipo_reporte    = solicitud.tipo_reporte,
            nombre          = nombre_auto,
            parametros      = params_json,
            estado          = "solicitado",
            id_usuario      = usuario_id,
            nombre_usuario  = nombre_usuario,
        )
        self.db.add(reporte)
        self.db.commit()
        self.db.refresh(reporte)

        # ── Estado: GENERANDO ───────────────────────────────────
        reporte.estado = "generando"
        self.db.commit()

        try:
            datos, columnas, cabeceras, resumen = self._preparar_datos(
                solicitud.tipo_reporte,
                solicitud.fecha_inicio,
                solicitud.fecha_fin,
            )

            resultado = generar_pdf(
                tipo_reporte   = solicitud.tipo_reporte,
                titulo         = nombre_auto,
                datos          = datos,
                columnas       = columnas,
                cabeceras      = cabeceras,
                resumen        = resumen,
                fecha_inicio   = solicitud.fecha_inicio,
                fecha_fin      = solicitud.fecha_fin,
                nombre_usuario = nombre_usuario,
            )

            # ── Estado: DISPONIBLE ──────────────────────────────
            reporte.estado         = "disponible"
            reporte.ruta_archivo   = resultado["ruta_archivo"]
            reporte.nombre_archivo = resultado["nombre_archivo"]
            reporte.tamano_bytes   = resultado["tamano_bytes"]
            reporte.num_registros  = resultado["num_registros"]
            reporte.fecha_generado = datetime.utcnow()
            self.db.commit()

            logger.info(
                f"Reporte '{solicitud.tipo_reporte}' generado: "
                f"{resultado['nombre_archivo']} "
                f"({resultado['num_registros']} registros, "
                f"{resultado['tamano_bytes']} bytes)"
            )

            # Registrar en auditoría
            self._registrar_auditoria_interna(
                modulo      = "reportes",
                accion      = "generar_reporte",
                tipo_entidad= "reporte",
                id_entidad  = reporte.id_reporte,
                descripcion = (
                    f"Reporte '{solicitud.tipo_reporte}' generado: "
                    f"{resultado['num_registros']} registros"
                ),
                id_usuario  = usuario_id,
                nombre_usuario = nombre_usuario,
            )

        except Exception as exc:
            # ── Estado: ERROR ───────────────────────────────────
            reporte.estado        = "error"
            reporte.mensaje_error = str(exc)[:490]
            self.db.commit()
            logger.error(f"Error generando reporte {solicitud.tipo_reporte}: {exc}")

        self.db.refresh(reporte)
        return self._reporte_a_response(reporte)

    def listar_reportes(self, usuario_id: int) -> List[ReporteListItem]:
        """Lista todos los reportes generados, ordenados por fecha descendente."""
        reportes = (
            self.db.query(Reporte)
            .order_by(Reporte.fecha_solicitud.desc())
            .all()
        )
        return [self._reporte_a_list_item(r) for r in reportes]

    def obtener_reporte(self, id_reporte: int) -> ReporteResponse:
        """Obtiene el estado y metadata de un reporte específico."""
        r = self._obtener_o_404(id_reporte)
        return self._reporte_a_response(r)

    def descargar_reporte(
        self, id_reporte: int, usuario_id: int, nombre_usuario: str
    ) -> FileResponse:
        """
        Retorna el archivo del reporte para descarga y transiciona
        al estado 'descargado' si corresponde.
        """
        r = self._obtener_o_404(id_reporte)

        if r.estado not in ("disponible", "descargado"):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"El reporte está en estado '{r.estado}' y no puede descargarse. "
                    "Solo los reportes en estado 'disponible' o 'descargado' son descargables."
                ),
            )

        if not r.ruta_archivo or not os.path.exists(r.ruta_archivo):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="El archivo del reporte no se encontró en el servidor.",
            )

        # Transición a descargado
        if r.estado == "disponible":
            r.estado         = "descargado"
            r.fecha_descarga = datetime.utcnow()
            self.db.commit()

        self._registrar_auditoria_interna(
            modulo       = "reportes",
            accion       = "exportar",
            tipo_entidad = "reporte",
            id_entidad   = r.id_reporte,
            descripcion  = f"Descarga del reporte '{r.nombre}'",
            id_usuario   = usuario_id,
            nombre_usuario = nombre_usuario,
        )

        media_type = (
            "application/pdf"
            if r.nombre_archivo.endswith(".pdf")
            else "application/json"
        )
        return FileResponse(
            path             = r.ruta_archivo,
            filename         = r.nombre_archivo,
            media_type       = media_type,
        )

    def reintentar_reporte(
        self, id_reporte: int, usuario_id: int, nombre_usuario: str
    ) -> ReporteResponse:
        """
        Reintento de un reporte en estado 'error'.
        Diagrama de estados: error → solicitado (→ generando → disponible).
        """
        r = self._obtener_o_404(id_reporte)
        if r.estado != "error":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Solo reportes en estado 'error' pueden reintentarse. Estado actual: '{r.estado}'.",
            )

        parametros = json.loads(r.parametros) if r.parametros else {}
        solicitud  = ReporteSolicitud(
            tipo_reporte = r.tipo_reporte,
            nombre       = r.nombre,
            fecha_inicio = parametros.get("fecha_inicio"),
            fecha_fin    = parametros.get("fecha_fin"),
        )
        # Reintentar crea un nuevo registro (trazabilidad limpia)
        return self.solicitar_reporte(solicitud, usuario_id, nombre_usuario)

    # ----------------------------------------------------------
    # RF-18 — AUDITORÍA
    # ----------------------------------------------------------

    def registrar_evento_auditoria(self, evento: AuditoriaCreate) -> int:
        """
        Registra un evento de auditoría (append-only, RNF-05).
        Retorna el id del registro creado.
        """
        registro = RegistroAuditoria(
            modulo         = evento.modulo,
            accion         = evento.accion,
            tipo_entidad   = evento.tipo_entidad,
            id_entidad     = evento.id_entidad,
            descripcion    = evento.descripcion,
            resultado      = evento.resultado,
            id_usuario     = evento.id_usuario,
            nombre_usuario = evento.nombre_usuario,
            rol_usuario    = evento.rol_usuario,
            ip_origen      = evento.ip_origen,
            dato_anterior  = evento.dato_anterior,
            dato_nuevo     = evento.dato_nuevo,
        )
        self.db.add(registro)
        self.db.commit()
        self.db.refresh(registro)
        return registro.id_auditoria

    def consultar_auditoria(
        self, filtros: AuditoriaFiltros
    ) -> Tuple[List[AuditoriaResponse], int]:
        """
        Consulta paginada del log de auditoría con filtros.
        Retorna (registros, total).
        """
        q = self.db.query(RegistroAuditoria)

        if filtros.modulo:
            q = q.filter(RegistroAuditoria.modulo == filtros.modulo)
        if filtros.accion:
            q = q.filter(RegistroAuditoria.accion == filtros.accion)
        if filtros.resultado:
            q = q.filter(RegistroAuditoria.resultado == filtros.resultado)
        if filtros.id_usuario:
            q = q.filter(RegistroAuditoria.id_usuario == filtros.id_usuario)
        if filtros.fecha_desde:
            q = q.filter(RegistroAuditoria.fecha_evento >= filtros.fecha_desde)
        if filtros.fecha_hasta:
            q = q.filter(RegistroAuditoria.fecha_evento <= filtros.fecha_hasta)

        total   = q.count()
        offset  = (filtros.page - 1) * filtros.page_size
        registros = (
            q.order_by(RegistroAuditoria.fecha_evento.desc())
            .offset(offset)
            .limit(filtros.page_size)
            .all()
        )

        return [
            AuditoriaResponse(
                id_auditoria   = r.id_auditoria,
                modulo         = r.modulo,
                accion         = r.accion,
                tipo_entidad   = r.tipo_entidad,
                id_entidad     = r.id_entidad,
                descripcion    = r.descripcion,
                resultado      = r.resultado,
                id_usuario     = r.id_usuario,
                nombre_usuario = r.nombre_usuario,
                rol_usuario    = r.rol_usuario,
                ip_origen      = r.ip_origen,
                dato_anterior  = r.dato_anterior,
                dato_nuevo     = r.dato_nuevo,
                fecha_evento   = r.fecha_evento,
            )
            for r in registros
        ], total

    # ----------------------------------------------------------
    # RESUMEN GLOBAL DEL SISTEMA
    # ----------------------------------------------------------

    def resumen_sistema(self) -> ResumenSistemaResponse:
        """
        Métricas globales del sistema para el panel del Administrador.
        Consulta todas las tablas del sistema via SQL directo.
        Si alguna tabla no existe (módulo no desplegado), retorna 0.
        """
        ahora      = datetime.utcnow()
        hace_7dias = ahora - timedelta(days=7)
        hoy_inicio = ahora.replace(hour=0, minute=0, second=0, microsecond=0)

        def _count(sql: str, params: dict = None) -> int:
            try:
                r = self.db.execute(text(sql), params or {}).fetchone()
                return int(r[0]) if r and r[0] else 0
            except Exception:
                return 0

        return ResumenSistemaResponse(
            total_usuarios      = _count("SELECT COUNT(*) FROM tbl_usuario"),
            usuarios_activos    = _count(
                "SELECT COUNT(*) FROM tbl_usuario WHERE estado_cuenta='activo'"
            ),
            total_cultivos      = _count("SELECT COUNT(*) FROM tbl_cultivo"),
            total_lotes         = _count("SELECT COUNT(*) FROM tbl_lote"),
            total_analisis_ia   = _count("SELECT COUNT(*) FROM tbl_analisis_ia"),
            analisis_ultima_semana = _count(
                "SELECT COUNT(*) FROM tbl_analisis_ia WHERE fecha_analisis >= :f",
                {"f": hace_7dias},
            ),
            lotes_en_proceso    = _count(
                "SELECT COUNT(*) FROM tbl_trazabilidad_lote "
                "WHERE estado IN ('registrado','disponible','en_analisis')"
            ),
            lotes_vendidos      = _count(
                "SELECT COUNT(*) FROM tbl_trazabilidad_lote WHERE estado='vendido'"
            ),
            total_analisis_precio  = _count("SELECT COUNT(*) FROM tbl_analisis_precio"),
            total_analisis_demanda = _count("SELECT COUNT(*) FROM tbl_analisis_demanda"),
            eventos_auditoria_hoy  = _count(
                "SELECT COUNT(*) FROM tbl_auditoria WHERE fecha_evento >= :f",
                {"f": hoy_inicio},
            ),
            errores_sistema_semana = _count(
                "SELECT COUNT(*) FROM tbl_auditoria "
                "WHERE resultado='fallido' AND fecha_evento >= :f",
                {"f": hace_7dias},
            ),
            reportes_generados  = _count(
                "SELECT COUNT(*) FROM tbl_reporte WHERE estado IN ('disponible','descargado')"
            ),
            fecha_actualizacion = ahora,
        )

    # ----------------------------------------------------------
    # PREPARACIÓN DE DATOS POR TIPO
    # ----------------------------------------------------------

    def _preparar_datos(
        self,
        tipo_reporte:  str,
        fecha_inicio:  Optional[datetime],
        fecha_fin:     Optional[datetime],
    ) -> Tuple[List[Dict], List[str], List[str], Dict]:
        """
        Despacha al preparador correcto según el tipo de reporte.
        Retorna (datos, columnas, cabeceras, resumen).
        """
        metodos = {
            "general":       self._datos_general,
            "cultivos":      self._datos_cultivos,
            "trazabilidad":  self._datos_trazabilidad,
            "fitosanitario": self._datos_fitosanitario,
            "ambiental":     self._datos_ambiental,
            "mercado":       self._datos_mercado,
            "usuarios":      self._datos_usuarios,
        }
        return metodos[tipo_reporte](fecha_inicio, fecha_fin)

    def _q(self, sql: str, params: dict = None) -> List[Any]:
        """Ejecuta SQL y retorna lista de Row. Silencia errores de tabla inexistente."""
        try:
            return self.db.execute(text(sql), params or {}).fetchall()
        except Exception as e:
            logger.warning(f"Consulta no disponible: {e}")
            return []

    def _datos_general(self, fi, ff):
        resumen = self.resumen_sistema()
        datos   = [
            {"indicador": "Total usuarios",          "valor": resumen.total_usuarios},
            {"indicador": "Usuarios activos",         "valor": resumen.usuarios_activos},
            {"indicador": "Total cultivos",           "valor": resumen.total_cultivos},
            {"indicador": "Total lotes",              "valor": resumen.total_lotes},
            {"indicador": "Análisis IA realizados",   "valor": resumen.total_analisis_ia},
            {"indicador": "Lotes en proceso",         "valor": resumen.lotes_en_proceso},
            {"indicador": "Lotes vendidos",           "valor": resumen.lotes_vendidos},
            {"indicador": "Eventos auditoría hoy",    "valor": resumen.eventos_auditoria_hoy},
            {"indicador": "Reportes generados",       "valor": resumen.reportes_generados},
        ]
        return datos, ["indicador", "valor"], ["Indicador", "Valor"], {
            "Fecha generación": datetime.utcnow().strftime("%d/%m/%Y %H:%M"),
            "Sistema":          settings.NOMBRE_ORGANIZACION,
        }

    def _datos_cultivos(self, fi, ff):
        filas = self._q("""
            SELECT c.id_cultivo, c.nombre_cultivo, c.ubicacion,
                   c.fecha_siembra, c.variedad,
                   u.nombre, u.apellido,
                   COUNT(l.id_lote) AS num_lotes
            FROM   tbl_cultivo c
            LEFT JOIN tbl_usuario u ON c.id_usuario = u.id_usuario
            LEFT JOIN tbl_lote    l ON l.id_cultivo = c.id_cultivo
            GROUP BY c.id_cultivo
            ORDER BY c.fecha_siembra DESC
        """)
        datos = [dict(zip(
            ["id","nombre_cultivo","ubicacion","fecha_siembra","variedad",
             "productor_nombre","productor_apellido","num_lotes"], r
        )) for r in filas]
        resumen = {
            "Total cultivos": len(datos),
            "Total lotes":    sum(d.get("num_lotes", 0) for d in datos),
        }
        cabs = ["ID","Cultivo","Ubicación","Fecha siembra","Variedad","Productor","Apellido","Lotes"]
        cols = ["id","nombre_cultivo","ubicacion","fecha_siembra","variedad",
                "productor_nombre","productor_apellido","num_lotes"]
        return datos, cols, cabs, resumen

    def _datos_trazabilidad(self, fi, ff):
        params = {}
        filtro_fecha = ""
        if fi:
            filtro_fecha += " AND t.fecha_creacion >= :fi"
            params["fi"] = fi
        if ff:
            filtro_fecha += " AND t.fecha_creacion <= :ff"
            params["ff"] = ff

        filas = self._q(f"""
            SELECT t.codigo_lote, t.variedad_cafe, t.estado,
                   t.kg_pergamino_seco, t.clasificacion_calidad,
                   t.comprador, t.precio_venta_kg,
                   t.fecha_creacion, t.fecha_venta
            FROM   tbl_trazabilidad_lote t
            WHERE  1=1 {filtro_fecha}
            ORDER BY t.fecha_creacion DESC
        """, params)
        datos = [dict(zip(
            ["codigo_lote","variedad","estado","kg","clasificacion",
             "comprador","precio_venta","fecha_registro","fecha_venta"], r
        )) for r in filas]
        vendidos = [d for d in datos if d.get("estado") == "vendido"]
        kg_total = sum(float(d.get("kg") or 0) for d in datos)
        resumen  = {
            "Total lotes":    len(datos),
            "Lotes vendidos": len(vendidos),
            "Kg totales":     f"{kg_total:,.0f}",
        }
        cabs = ["Código","Variedad","Estado","Kg","Calidad","Comprador","Precio/kg","Registro","Venta"]
        cols = ["codigo_lote","variedad","estado","kg","clasificacion",
                "comprador","precio_venta","fecha_registro","fecha_venta"]
        return datos, cols, cabs, resumen

    def _datos_fitosanitario(self, fi, ff):
        params = {}
        filtro = ""
        if fi:
            filtro += " AND a.fecha_analisis >= :fi"; params["fi"] = fi
        if ff:
            filtro += " AND a.fecha_analisis <= :ff"; params["ff"] = ff

        filas = self._q(f"""
            SELECT a.id_analisis, a.resultado, a.recomendacion,
                   a.fecha_analisis, c.nombre_cultivo, c.ubicacion
            FROM   tbl_analisis_ia a
            JOIN   tbl_cultivo     c ON a.id_cultivo = c.id_cultivo
            WHERE  1=1 {filtro}
            ORDER BY a.fecha_analisis DESC
        """, params)
        datos = [dict(zip(
            ["id","resultado","recomendacion","fecha","cultivo","ubicacion"], r
        )) for r in filas]
        resumen = {
            "Total análisis": len(datos),
            "Período": f"{fi.strftime('%d/%m/%Y') if fi else 'Todo'} - {ff.strftime('%d/%m/%Y') if ff else 'Hoy'}",
        }
        cabs = ["ID","Diagnóstico","Recomendación","Fecha","Cultivo","Ubicación"]
        cols = ["id","resultado","recomendacion","fecha","cultivo","ubicacion"]
        return datos, cols, cabs, resumen

    def _datos_ambiental(self, fi, ff):
        params = {}
        filtro = ""
        if fi:
            filtro += " AND s.fecha_lectura >= :fi"; params["fi"] = fi
        if ff:
            filtro += " AND s.fecha_lectura <= :ff"; params["ff"] = ff

        filas = self._q(f"""
            SELECT s.tipo_sensor, s.valor, s.unidad,
                   s.fecha_lectura, s.alerta_activa,
                   c.nombre_cultivo
            FROM   tbl_lectura_sensor s
            JOIN   tbl_sensor         se ON s.id_sensor = se.id_sensor
            JOIN   tbl_cultivo        c  ON se.id_cultivo = c.id_cultivo
            WHERE  1=1 {filtro}
            ORDER BY s.fecha_lectura DESC
            LIMIT 500
        """, params)
        datos = [dict(zip(
            ["tipo","valor","unidad","fecha","alerta","cultivo"], r
        )) for r in filas]
        alertas = [d for d in datos if d.get("alerta")]
        resumen = {
            "Total lecturas": len(datos),
            "Alertas activas": len(alertas),
        }
        cabs = ["Sensor","Valor","Unidad","Fecha","Alerta","Cultivo"]
        cols = ["tipo","valor","unidad","fecha","alerta","cultivo"]
        return datos, cols, cabs, resumen

    def _datos_mercado(self, fi, ff):
        filas = self._q("""
            SELECT ap.tendencia, ap.precio_promedio, ap.precio_minimo,
                   ap.precio_maximo, ap.variacion_pct,
                   ap.precio_proyectado, ap.alerta_activa,
                   ap.fecha_analisis
            FROM   tbl_analisis_precio ap
            ORDER BY ap.fecha_analisis DESC
            LIMIT 100
        """)
        datos = [dict(zip(
            ["tendencia","prom","min","max","variacion",
             "proyectado","alerta","fecha"], r
        )) for r in filas]
        resumen = {"Total análisis de precio": len(datos)}
        cabs = ["Tendencia","Promedio","Mínimo","Máximo","Var%","Proyectado","Alerta","Fecha"]
        cols = ["tendencia","prom","min","max","variacion","proyectado","alerta","fecha"]
        return datos, cols, cabs, resumen

    def _datos_usuarios(self, fi, ff):
        filas = self._q("""
            SELECT u.id_usuario, u.nombre, u.apellido, u.correo,
                   r.nombre_rol, u.estado_cuenta, u.fecha_registro
            FROM   tbl_usuario u
            JOIN   tbl_rol     r ON u.id_rol = r.id_rol
            ORDER BY u.fecha_registro DESC
        """)
        datos = [dict(zip(
            ["id","nombre","apellido","correo","rol","estado","fecha_registro"], r
        )) for r in filas]
        activos = [d for d in datos if d.get("estado") == "activo"]
        resumen = {
            "Total usuarios": len(datos),
            "Activos":        len(activos),
            "Inactivos":      len(datos) - len(activos),
        }
        cabs = ["ID","Nombre","Apellido","Correo","Rol","Estado","Registro"]
        cols = ["id","nombre","apellido","correo","rol","estado","fecha_registro"]
        return datos, cols, cabs, resumen

    # ----------------------------------------------------------
    # HELPERS PRIVADOS
    # ----------------------------------------------------------

    def _obtener_o_404(self, id_reporte: int) -> Reporte:
        r = self.db.query(Reporte).filter(Reporte.id_reporte == id_reporte).first()
        if not r:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Reporte ID {id_reporte} no encontrado.",
            )
        return r

    def _registrar_auditoria_interna(self, **kwargs):
        """Registra un evento de auditoría sin lanzar excepción si falla."""
        try:
            self.registrar_evento_auditoria(AuditoriaCreate(**kwargs))
        except Exception as e:
            logger.warning(f"No se pudo registrar auditoría: {e}")

    def _reporte_a_response(self, r: Reporte) -> ReporteResponse:
        return ReporteResponse(
            id_reporte     = r.id_reporte,
            tipo_reporte   = r.tipo_reporte,
            nombre         = r.nombre,
            estado         = r.estado,
            estado_label   = ESTADOS_LABEL.get(r.estado, r.estado),
            ruta_archivo   = r.ruta_archivo,
            nombre_archivo = r.nombre_archivo,
            tamano_kb      = round(r.tamano_bytes / 1024, 1) if r.tamano_bytes else None,
            num_registros  = r.num_registros,
            mensaje_error  = r.mensaje_error,
            nombre_usuario = r.nombre_usuario,
            fecha_solicitud = r.fecha_solicitud,
            fecha_generado  = r.fecha_generado,
            fecha_descarga  = r.fecha_descarga,
        )

    def _reporte_a_list_item(self, r: Reporte) -> ReporteListItem:
        return ReporteListItem(
            id_reporte     = r.id_reporte,
            tipo_reporte   = r.tipo_reporte,
            nombre         = r.nombre,
            estado         = r.estado,
            estado_label   = ESTADOS_LABEL.get(r.estado, r.estado),
            tamano_kb      = round(r.tamano_bytes / 1024, 1) if r.tamano_bytes else None,
            num_registros  = r.num_registros,
            nombre_usuario = r.nombre_usuario,
            fecha_solicitud = r.fecha_solicitud,
            fecha_generado  = r.fecha_generado,
        )
