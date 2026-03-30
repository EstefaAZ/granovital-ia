# ==============================================================
# modulo_05_trazabilidad / app/util/qr_generator.py
# Generador de codigos QR — RN-05
# BUG-039 FIX: QR real usando libreria qrcode[svg]
#   Instalar: pip install qrcode[pil] qrcode[svg]
# ==============================================================

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def generar_url_qr(codigo_lote: str, url_base: str) -> str:
    """Genera la URL publica del QR para el consumidor."""
    url = f"{url_base}/trazabilidad/{codigo_lote}"
    logger.info(f"QR generado para lote {codigo_lote}: {url}")
    return url


def generar_svg_qr(codigo_lote: str, url_base: str) -> str:
    """
    BUG-039 FIX: Genera un QR SVG real y escaneable usando la
    libreria qrcode. Si no esta instalada, cae en el placeholder
    con advertencia clara en el log.

    Instalar dependencia: pip install "qrcode[svg]"
    """
    url = generar_url_qr(codigo_lote, url_base)
    color = "#6f3a1b"

    # Intentar generar QR real
    try:
        import qrcode
        import qrcode.image.svg
        import io

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=4,
            border=2,
        )
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(
            image_factory=qrcode.image.svg.SvgFillImage,
            fill_color=color,
            back_color="white",
        )
        buf = io.BytesIO()
        img.save(buf)
        svg_bytes = buf.getvalue().decode("utf-8")

        # Agregar etiqueta de codigo debajo del QR
        svg_bytes = svg_bytes.replace(
            "</svg>",
            f'''  <text x="50%" y="98%" text-anchor="middle"
            font-family="Arial" font-size="8" fill="{color}">
    {codigo_lote} — GranoVital IA
  </text>
</svg>''',
        )
        logger.info(f"QR real generado para lote {codigo_lote}")
        return svg_bytes

    except ImportError:
        logger.warning(
            "Libreria qrcode no instalada. Usando placeholder. "
            "Ejecuta: pip install \"qrcode[svg]\""
        )
        return _placeholder_svg(codigo_lote, url, color)


def _placeholder_svg(codigo_lote: str, url: str, color: str) -> str:
    """SVG decorativo de respaldo cuando qrcode no esta instalado."""
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="200" height="230" viewBox="0 0 200 230">
  <rect width="200" height="230" fill="#f9f3ee" rx="12"/>
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
  <text x="100" y="212" text-anchor="middle" font-family="Arial" font-size="7" fill="#c0392b">
    ⚠ QR NO ESCANEABLE — instalar qrcode[svg]
  </text>
</svg>'''
