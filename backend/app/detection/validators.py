"""Validadores de dígitos/letras de control para identificadores españoles.

Se usan en la capa 1 para descartar falsos positivos: una cadena que "parece"
un DNI pero cuya letra de control no cuadra NO se marca como DNI (aunque puede
seguir siendo detectada por otras capas si procede).
"""

import re

# Tabla oficial de letras del DNI/NIE (orden = resto de dividir el número entre 23)
LETRAS_DNI = "TRWAGMYFPDXBNJZSQVHLCKE"


def validar_dni(texto: str) -> bool:
    """Valida un DNI español: 8 dígitos + letra de control (módulo 23)."""
    limpio = re.sub(r"[\s.\-]", "", texto).upper()
    if not re.fullmatch(r"\d{8}[A-Z]", limpio):
        return False
    numero = int(limpio[:8])
    return LETRAS_DNI[numero % 23] == limpio[8]


def validar_nie(texto: str) -> bool:
    """Valida un NIE: X/Y/Z + 7 dígitos + letra. X→0, Y→1, Z→2 y módulo 23."""
    limpio = re.sub(r"[\s.\-]", "", texto).upper()
    if not re.fullmatch(r"[XYZ]\d{7}[A-Z]", limpio):
        return False
    numero = int("XYZ".index(limpio[0]) * 10**7 + int(limpio[1:8]))
    return LETRAS_DNI[numero % 23] == limpio[8]


def validar_nuss(texto: str) -> bool:
    """Valida un número de la Seguridad Social (NUSS/NAF), 11-12 dígitos.

    Estructura: PP NNNNNNNN CC (provincia, secuencial, control).
    Regla oficial (módulo 97):
      - si el secuencial es < 10.000.000: control = (provincia*10.000.000 + secuencial) % 97
      - si no: control = int(provincia + secuencial concatenados) % 97
    """
    limpio = re.sub(r"[\s./\-]", "", texto)
    if not re.fullmatch(r"\d{11,12}", limpio):
        return False
    limpio = limpio.zfill(12)
    provincia, secuencial, control = int(limpio[:2]), int(limpio[2:10]), int(limpio[10:])
    if secuencial < 10_000_000:
        base = provincia * 10_000_000 + secuencial
    else:
        base = int(str(provincia) + str(secuencial))
    return base % 97 == control


def es_telefono_es(texto: str) -> bool:
    """Comprueba que un candidato a teléfono español tiene prefijo y longitud válidos."""
    limpio = re.sub(r"[\s.\-()]", "", texto)
    limpio = limpio.removeprefix("+34").removeprefix("0034")
    # Móviles (6,7), fijos (8,9) — 9 dígitos en total
    return bool(re.fullmatch(r"[6789]\d{8}", limpio))


def es_codigo_postal_es(texto: str) -> bool:
    """Código postal español válido: 01000–52999."""
    if not re.fullmatch(r"\d{5}", texto.strip()):
        return False
    return 1 <= int(texto[:2]) <= 52
