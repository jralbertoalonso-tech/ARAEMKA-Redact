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


# ──────────────────────────────────────────────────────────────────────────
# Identificadores económicos y de empresa (uso general, no solo sanitario)
# ──────────────────────────────────────────────────────────────────────────

def validar_iban(texto: str) -> bool:
    """Valida un IBAN de cualquier país europeo (norma ISO 13616, módulo 97).

    Un IBAN es correcto si, al mover los 4 primeros caracteres al final y
    convertir las letras en números (A=10 … Z=35), el resultado módulo 97 es 1.
    """
    limpio = re.sub(r"[\s\-]", "", texto).upper()
    if not re.fullmatch(r"[A-Z]{2}\d{2}[A-Z0-9]{10,30}", limpio):
        return False
    reordenado = limpio[4:] + limpio[:4]
    numerico = "".join(str(int(c, 36)) for c in reordenado)
    return int(numerico) % 97 == 1


def validar_cif(texto: str) -> bool:
    """Valida un CIF/NIF de entidad española (letra + 7 dígitos + control).

    El control se obtiene sumando los dígitos pares y el doblado de los impares
    (sumando las cifras del resultado); según la letra inicial el control es un
    dígito, una letra, o cualquiera de los dos.
    """
    limpio = re.sub(r"[\s.\-]", "", texto).upper()
    if not re.fullmatch(r"[ABCDEFGHJKLMNPQRSUVW]\d{7}[0-9A-J]", limpio):
        return False
    inicial, digitos, control = limpio[0], limpio[1:8], limpio[8]

    pares = sum(int(d) for d in digitos[1::2])
    impares = 0
    for d in digitos[0::2]:
        doble = int(d) * 2
        impares += doble // 10 + doble % 10
    resto = (pares + impares) % 10
    digito_control = (10 - resto) % 10
    letra_control = "JABCDEFGHI"[digito_control]

    if inicial in "PQRSNW":            # control siempre letra
        return control == letra_control
    if inicial in "ABEH":              # control siempre dígito
        return control == str(digito_control)
    return control in (str(digito_control), letra_control)


def validar_tarjeta(texto: str) -> bool:
    """Valida una tarjeta de pago con el algoritmo de Luhn (13-19 dígitos)."""
    limpio = re.sub(r"[\s\-]", "", texto)
    if not re.fullmatch(r"\d{13,19}", limpio):
        return False
    suma, alterno = 0, False
    for c in reversed(limpio):
        d = int(c)
        if alterno:
            d *= 2
            if d > 9:
                d -= 9
        suma += d
        alterno = not alterno
    return suma % 10 == 0


def es_matricula_es(texto: str) -> bool:
    """Matrícula española: actual (1234 BCD) o antigua provincial (M-1234-AB).

    En el formato actual las tres letras no incluyen vocales ni Ñ/Q, lo que
    evita confundir con siglas y códigos.
    """
    limpio = re.sub(r"[\s\-]", "", texto).upper()
    if re.fullmatch(r"\d{4}[BCDFGHJKLMNPRSTVWXYZ]{3}", limpio):
        return True
    return bool(re.fullmatch(r"[A-Z]{1,2}\d{4}[A-Z]{1,2}", limpio))


def validar_referencia_catastral(texto: str) -> bool:
    """Referencia catastral: 20 caracteres alfanuméricos con letras y dígitos.

    No se comprueban los dos dígitos de control (su algoritmo no es público de
    forma estable); se exige la estructura y que mezcle letras y números, lo que
    ya descarta la mayoría de códigos ajenos.
    """
    limpio = re.sub(r"[\s\-]", "", texto).upper()
    if not re.fullmatch(r"[A-Z0-9]{20}", limpio):
        return False
    return bool(re.search(r"[A-Z]", limpio)) and bool(re.search(r"\d", limpio))


def es_pasaporte_es(texto: str) -> bool:
    """Pasaporte español: 3 letras + 6 dígitos (actual) o 2 letras + 6 dígitos."""
    limpio = re.sub(r"[\s\-]", "", texto).upper()
    return bool(re.fullmatch(r"[A-Z]{2,3}\d{6}", limpio))
