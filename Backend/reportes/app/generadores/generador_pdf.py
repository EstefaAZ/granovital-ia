# ==============================================================
# modulo_07_reportes / app/generadores/generador_pdf.py
#
# Generador de reportes en formato PDF usando reportlab.
# El Diagrama de Actividad del documento oficial especifica:
#   Usuario: seleccionar tipo → elegir tipo → confirmar
#   Sistema: consultar BD → generar PDF → mostrar descarga
#
# DECISIÓN TÉCNICA:
#   Se usa reportlab (Pure Python, sin dependencias del SO)
#   porque es la biblioteca estándar de facto para generación
#   programática de PDFs en Python. Es adecuada para entornos
#   rurales con infraestructura limitada.
#   Si reportlab no está disponible, el módulo genera un JSON
#   estructurado como fallback (modo degradado).
#
# RF-18: "reportes estadísticos en PDF o Excel" (del Test Plan
#         CP-08, que menciona ambos formatos).
# ==============================================================

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.core.config import settings

# Intentar importar reportlab (modo completo vs degradado)
try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
    )
    REPORTLAB_OK = True
except ImportError:
    REPORTLAB_OK = False


# Paleta de colores GranoVital
COLOR_CAFE    = (0.435, 0.227, 0.106)   # #6f3a1b
COLOR_VERDE   = (0.176, 0.478, 0.227)   # #2d7a3a
COLOR_HEADER  = (0.412, 0.322, 0.235)   # encabezados de tabla


def _asegurar_directorio():
    os.makedirs(settings.REPORTES_DIR, exist_ok=True)


def _nombre_archivo(tipo_reporte: str) -> str:
    ts = datetime.now(timezone.utc)  # BUG-021 FIX.strftime("%Y%m%d_%H%M%S")
    return f"granovital_{tipo_reporte}_{ts}.pdf"


def _color_rl(rgb_tuple):
    """Convierte tupla (r,g,b) en 0-1 a color reportlab."""
    from reportlab.lib.colors import Color
    return Color(*rgb_tuple)


def generar_pdf(
    tipo_reporte:  str,
    titulo:        str,
    datos:         List[Dict[str, Any]],
    columnas:      List[str],
    cabeceras:     List[str],
    resumen:       Optional[Dict[str, Any]] = None,
    fecha_inicio:  Optional[datetime] = None,
    fecha_fin:     Optional[datetime] = None,
    nombre_usuario: str = "Administrador",
) -> Dict[str, Any]:
    """
    Genera un PDF del reporte y lo guarda en REPORTES_DIR.

    Retorna:
      {
        "ruta_archivo":   str,
        "nombre_archivo": str,
        "tamano_bytes":   int,
        "num_registros":  int,
      }

    Si reportlab no está disponible, genera un JSON de respaldo
    y retorna la ruta a ese archivo.
    """
    _asegurar_directorio()
    nombre_arch = _nombre_archivo(tipo_reporte)
    ruta_completa = os.path.join(settings.REPORTES_DIR, nombre_arch)

    if REPORTLAB_OK:
        return _generar_con_reportlab(
            ruta_completa, nombre_arch, titulo, tipo_reporte,
            datos, columnas, cabeceras, resumen,
            fecha_inicio, fecha_fin, nombre_usuario,
        )
    else:
        return _generar_json_fallback(
            ruta_completa, nombre_arch, tipo_reporte,
            datos, resumen, fecha_inicio, fecha_fin,
        )


def _generar_con_reportlab(
    ruta, nombre_arch, titulo, tipo_reporte,
    datos, columnas, cabeceras, resumen,
    fecha_inicio, fecha_fin, nombre_usuario,
) -> Dict[str, Any]:

    doc    = SimpleDocTemplate(
        ruta, pagesize=A4,
        topMargin=2*cm, bottomMargin=2*cm,
        leftMargin=2*cm, rightMargin=2*cm,
    )
    estilos = getSampleStyleSheet()
    historia = []

    c_cafe  = _color_rl(COLOR_CAFE)
    c_verde = _color_rl(COLOR_VERDE)

    # ── Encabezado ────────────────────────────────────────────
    estilo_titulo = ParagraphStyle(
        "Titulo",
        parent=estilos["Title"],
        fontSize=18,
        textColor=c_cafe,
        spaceAfter=4,
    )
    estilo_sub = ParagraphStyle(
        "Sub",
        parent=estilos["Normal"],
        fontSize=10,
        textColor=colors.HexColor("#7a5c3a"),
        spaceAfter=2,
    )
    estilo_normal = ParagraphStyle(
        "Normal2",
        parent=estilos["Normal"],
        fontSize=9,
        spaceAfter=3,
    )

    historia.append(Paragraph(settings.NOMBRE_ORGANIZACION, estilo_sub))
    historia.append(Paragraph(titulo, estilo_titulo))

    # Período y metadata
    periodo_texto = ""
    if fecha_inicio and fecha_fin:
        periodo_texto = (
            f"Período: {fecha_inicio.strftime('%d/%m/%Y')} "
            f"— {fecha_fin.strftime('%d/%m/%Y')}"
        )
    elif fecha_inicio:
        periodo_texto = f"Desde: {fecha_inicio.strftime('%d/%m/%Y')}"

    historia.append(Paragraph(
        f"Generado por: {nombre_usuario} "
        f"| Fecha: {datetime.now(timezone.utc)  # BUG-021 FIX.strftime('%d/%m/%Y %H:%M')} UTC",
        estilo_sub,
    ))
    if periodo_texto:
        historia.append(Paragraph(periodo_texto, estilo_sub))
    historia.append(Spacer(1, 0.4*cm))

    # ── Sección de resumen ────────────────────────────────────
    if resumen:
        historia.append(Paragraph("Resumen ejecutivo", ParagraphStyle(
            "H2", parent=estilos["Heading2"], fontSize=12,
            textColor=c_cafe, spaceBefore=8,
        )))
        resumen_data = [["Indicador", "Valor"]]
        for k, v in resumen.items():
            resumen_data.append([str(k), str(v)])

        tabla_res = Table(resumen_data, colWidths=[9*cm, 7*cm])
        tabla_res.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), c_cafe),
            ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
            ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",   (0, 0), (-1, 0), 10),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f9f3ee")]),
            ("FONTSIZE",   (0, 1), (-1, -1), 9),
            ("GRID",       (0, 0), (-1, -1), 0.5, colors.HexColor("#d4b896")),
            ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        historia.append(tabla_res)
        historia.append(Spacer(1, 0.5*cm))

    # ── Tabla de datos ─────────────────────────────────────────
    if datos and cabeceras:
        historia.append(Paragraph(
            f"Detalle ({len(datos)} registro(s))",
            ParagraphStyle("H2", parent=estilos["Heading2"],
                           fontSize=12, textColor=c_cafe, spaceBefore=8),
        ))

        tabla_datos = [cabeceras]
        for fila in datos:
            row = []
            for col in columnas:
                val = fila.get(col, "")
                if isinstance(val, datetime):
                    val = val.strftime("%d/%m/%Y %H:%M")
                elif val is None:
                    val = "—"
                row.append(str(val)[:80])  # truncar celdas muy largas
            tabla_datos.append(row)

        # Ancho dinámico de columnas
        n_cols    = len(cabeceras)
        ancho_disp = 17 * cm
        col_w     = [ancho_disp / n_cols] * n_cols

        tabla = Table(tabla_datos, colWidths=col_w, repeatRows=1)
        tabla.setStyle(TableStyle([
            ("BACKGROUND",  (0, 0), (-1, 0), c_cafe),
            ("TEXTCOLOR",   (0, 0), (-1, 0), colors.white),
            ("FONTNAME",    (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",    (0, 0), (-1, 0), 8),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1),
             [colors.white, colors.HexColor("#f9f3ee")]),
            ("FONTSIZE",    (0, 1), (-1, -1), 7.5),
            ("GRID",        (0, 0), (-1, -1), 0.4, colors.HexColor("#d4b896")),
            ("VALIGN",      (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING",  (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("WORDWRAP",    (0, 0), (-1, -1), True),
        ]))
        historia.append(tabla)

    # ── Pie de página ─────────────────────────────────────────
    historia.append(Spacer(1, 1*cm))
    historia.append(Paragraph(
        f"— {settings.NOMBRE_ORGANIZACION} · Reporte generado automáticamente —",
        ParagraphStyle("Pie", parent=estilos["Normal"],
                       fontSize=7, textColor=colors.grey, alignment=1),
    ))

    doc.build(historia)

    tamano = os.path.getsize(ruta)
    return {
        "ruta_archivo":   ruta,
        "nombre_archivo": nombre_arch,
        "tamano_bytes":   tamano,
        "num_registros":  len(datos),
    }


def _generar_json_fallback(
    ruta, nombre_arch, tipo_reporte, datos, resumen, fecha_inicio, fecha_fin,
) -> Dict[str, Any]:
    """
    Modo degradado: cuando reportlab no está disponible genera JSON.
    El nombre de archivo cambia a .json para que el cliente lo detecte.
    """
    nombre_json = nombre_arch.replace(".pdf", ".json")
    ruta_json   = ruta.replace(".pdf", ".json")

    payload = {
        "tipo_reporte": tipo_reporte,
        "generado_en":  datetime.now(timezone.utc)  # BUG-021 FIX.isoformat(),
        "resumen":      resumen or {},
        "registros":    len(datos),
        "datos":        datos,
        "nota": (
            "Reporte generado en formato JSON porque reportlab "
            "no está instalado. Instale con: pip install reportlab"
        ),
    }
    with open(ruta_json, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, default=str)

    tamano = os.path.getsize(ruta_json)
    return {
        "ruta_archivo":   ruta_json,
        "nombre_archivo": nombre_json,
        "tamano_bytes":   tamano,
        "num_registros":  len(datos),
    }
