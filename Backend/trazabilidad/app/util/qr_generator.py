# ==============================================================
# modulo_05_trazabilidad / app/util/qr_generator.py
# Generador de codigos QR para consulta publica - RN-05
#
# Genera la URL publica que el consumidor escanea para ver
# la informacion de trazabilidad y calidad del cafe.
# El QR apunta al endpoint publico que no requiere autenticacion
# y solo expone los campos autorizados por RN-05.
# ==============================================================

import base64
import hashlib
import io
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def generar_url_qr(codigo_lote: str, url_base: str) -> str:
    """
    Genera la URL publica del QR para el consumidor.
    
    La URL apunta al endpoint publico:
    GET /api/v1/trazabilidad/publico/{codigo_lote}
    
    Este endpoint no requiere autenticacion (RN-05) y solo
    expone informacion de trazabilidad y calidad, nunca
    datos internos como precios internos, IDs de sistema
    o informacion de usuarios.
    """
    url = f"{url_base}/trazabilidad/{codigo_lote}"
    logger.info(f"QR generado para lote {codigo_lote}: {url}")
    return url


def generar_svg_qr(codigo_lote: str, url_base: str) -> str:
    """
    Genera una representacion SVG simplificada del QR.
    En produccion se usa la libreria 'qrcode' con backend SVG.
    
    Este SVG de placeholder permite desarrollo y pruebas
    sin dependencia de librerías graficas en entornos rurales
    con instalaciones limitadas.
    
    Para produccion, instalar: pip install qrcode[pil] svgwrite
    y reemplazar con:
        import qrcode
        import qrcode.image.svg
        qr = qrcode.make(url, image_factory=qrcode.image.svg.SvgImage)
    """
    url   = generar_url_qr(codigo_lote, url_base)
    color = "#6f3a1b"   # cafe GranoVital

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="200" height="220" viewBox="0 0 200 220">
  <!-- QR Placeholder - GranoVital IA -->
  <rect width="200" height="220" fill="#f9f3ee" rx="12"/>
  <rect x="20" y="20" width="160" height="160" fill="white" stroke="{color}" stroke-width="2" rx="4"/>
  <rect x="30" y="30" width="50" height="50" fill="{color}" rx="2"/>
  <rect x="36" y="36" width="38" height="38" fill="white" rx="1"/>
  <rect x="42" y="42" width="26" height="26" fill="{color}" rx="1"/>
  <rect x="120" y="30" width="50" height="50" fill="{color}" rx="2"/>
  <rect x="126" y="36" width="38" height="38" fill="white" rx="1"/>
  <rect x="132" y="42" width="26" height="26" fill="{color}" rx="1"/>
  <rect x="30" y="120" width="50" height="50" fill="{color}" rx="2"/>
  <rect x="36" y="126" width="38" height="38" fill="white" rx="1"/>
  <rect x="42" y="132" width="26" height="26" fill="{color}" rx="1"/>
  <text x="100" y="198" text-anchor="middle" font-family="Arial" font-size="9" fill="{color}">
    {codigo_lote}
  </text>
  <text x="100" y="212" text-anchor="middle" font-family="Arial" font-size="7" fill="#9a7a5a">
    GranoVital IA — Escanea para ver trazabilidad
  </text>
</svg>"""
    return svg


