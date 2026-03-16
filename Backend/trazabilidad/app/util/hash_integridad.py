# ==============================================================
# modulo_05_trazabilidad / app/util/hash_integridad.py
# Hash de integridad — RN-04 / RNF-05
#
# Calcula y verifica el hash SHA-256 del estado validado del
# lote de cafe para detectar modificaciones no autorizadas.
#
# RN-04: el hash se genera en la transicion a 'aprobado' y se
# almacena en tbl_trazabilidad_lote.hash_integridad.
# Cualquier modificacion posterior de los campos criticos
# producira un hash diferente, permitiendo detectar alteraciones
# (RNF-05 — integridad de datos de trazabilidad).
#
# Campos incluidos en el hash (criticos de calidad y origen):
#   codigo_lote, variedad_cafe, fecha_cosecha,
#   kg_cereza_cosechados, clasificacion_calidad,
#   humedad_final_pct, numero_defectos, sal_del_sistema
#
# Los campos operativos como observaciones, comprador o destino
# NO se incluyen para permitir actualizaciones normales sin
# invalidar la integridad del lote validado.
# ==============================================================

import hashlib
from typing import Optional


def calcular_hash_lote(
    codigo_lote:     str,
    variedad_cafe:   str,
    fecha_cosecha:   str,
    kg_cereza:       float,
    clasificacion:   str,
    humedad:         Optional[float],
    numero_defectos: Optional[int],
    sal:             str,
) -> str:
    """
    Calcula el hash SHA-256 del estado validado del lote.

    Parametros:
      codigo_lote     Codigo unico legible del lote (GV-AAAA-NNNN)
      variedad_cafe   Variedad del grano (castillo, colombia, etc.)
      fecha_cosecha   Fecha de cosecha en formato string ISO
      kg_cereza       Kilogramos de cereza cosechados
      clasificacion   Categoria FNC asignada (supremo, excelso, etc.)
      humedad         Porcentaje de humedad final del grano
      numero_defectos Numero de defectos detectados en muestra 300g
      sal             Sal del sistema para evitar ataques de precomputo

    Retorna:
      str  Hash hexadecimal SHA-256 de 64 caracteres
    """
    contenido = (
        f"{codigo_lote}|{variedad_cafe}|{fecha_cosecha}|"
        f"{kg_cereza}|{clasificacion}|{humedad}|"
        f"{numero_defectos}|{sal}"
    )
    return hashlib.sha256(contenido.encode("utf-8")).hexdigest()


def verificar_hash_lote(
    hash_almacenado: str,
    codigo_lote:     str,
    variedad_cafe:   str,
    fecha_cosecha:   str,
    kg_cereza:       float,
    clasificacion:   str,
    humedad:         Optional[float],
    numero_defectos: Optional[int],
    sal:             str,
) -> bool:
    """
    Verifica si el hash almacenado coincide con el calculado
    a partir de los datos actuales del lote.

    Retorna:
      True  si el registro es integro (no fue alterado)
      False si hay discrepancia — posible alteracion no autorizada

    Uso tipico (auditoria administrativa):
      integro = verificar_hash_lote(
          lote.hash_integridad,
          lote.codigo_lote, lote.variedad_cafe,
          str(lote.fecha_cosecha), float(lote.kg_cereza_cosechados),
          lote.clasificacion_calidad, lote.humedad_final_pct,
          lote.numero_defectos, settings.HASH_INTEGRIDAD_SAL
      )
      if not integro:
          raise AlertaIntegridad(f"Lote {lote.codigo_lote} alterado")
    """
    hash_calculado = calcular_hash_lote(
        codigo_lote, variedad_cafe, fecha_cosecha,
        kg_cereza, clasificacion, humedad, numero_defectos, sal,
    )
    return hash_almacenado == hash_calculado
