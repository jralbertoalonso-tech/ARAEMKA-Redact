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


# ══════════════════════════════════════════════════════════════════════════
# Identificadores en inglés — Reino Unido y Estados Unidos
# ══════════════════════════════════════════════════════════════════════════
# Se usan en el motor de detección inglés (documentos en inglés). Igual que los
# españoles, los que llevan dígito de control se validan matemáticamente para
# descartar falsos positivos.

def validar_nhs(texto: str) -> bool:
    """Número del NHS británico: 10 dígitos con dígito de control módulo 11.

    Los 9 primeros dígitos se ponderan 10, 9, 8… 2; el control es
    11 − (suma ponderada mód 11). Un resto de 0 → control 0; un resto de 1 hace
    el número inválido (no existe control «10»).
    """
    limpio = re.sub(r"[\s\-]", "", texto)
    if not re.fullmatch(r"\d{10}", limpio):
        return False
    suma = sum(int(limpio[i]) * (10 - i) for i in range(9))
    control = 11 - (suma % 11)
    if control == 11:
        control = 0
    elif control == 10:
        return False
    return control == int(limpio[9])


def es_nino(texto: str) -> bool:
    """National Insurance Number británico: 2 letras + 6 dígitos + 1 letra (A-D).

    No lleva dígito de control, pero sí reglas de formato estrictas: ciertas
    letras y prefijos no se emiten nunca, lo que descarta la mayoría de códigos
    ajenos con la misma forma.
    """
    limpio = re.sub(r"[\s\-]", "", texto).upper()
    if not re.fullmatch(r"[A-Z]{2}\d{6}[A-D]", limpio):
        return False
    primera, segunda = limpio[0], limpio[1]
    # Letras que nunca se usan en cada posición
    if primera in "DFIQUV" or segunda in "DFIOQUV":
        return False
    # Prefijos administrativos no asignables
    if limpio[:2] in {"BG", "GB", "NK", "KN", "TN", "NT", "ZZ"}:
        return False
    return True


def es_ssn(texto: str) -> bool:
    """Número de la Seguridad Social de EE. UU. (SSN): AAA-GG-SSSS.

    No tiene dígito de control; se validan los rangos que la SSA nunca emite:
    área 000, 666 o 900-999; grupo 00; serie 0000.
    """
    limpio = re.sub(r"[\s\-]", "", texto)
    if not re.fullmatch(r"\d{9}", limpio):
        return False
    area, grupo, serie = int(limpio[:3]), int(limpio[3:5]), int(limpio[5:])
    if area == 0 or area == 666 or area >= 900:
        return False
    if grupo == 0 or serie == 0:
        return False
    return True


def es_itin(texto: str) -> bool:
    """ITIN estadounidense: empieza por 9 y el grupo cae en rangos reservados.

    Formato 9XX-GG-XXXX con GG en 50-65, 70-88, 90-92 o 94-99. Distingue el ITIN
    (contribuyentes sin SSN) de un SSN normal.
    """
    limpio = re.sub(r"[\s\-]", "", texto)
    if not re.fullmatch(r"9\d{8}", limpio):
        return False
    grupo = int(limpio[3:5])
    return 50 <= grupo <= 65 or 70 <= grupo <= 88 or 90 <= grupo <= 92 or 94 <= grupo <= 99


def es_codigo_postal_uk(texto: str) -> bool:
    """Código postal británico (p. ej. «SW1A 1AA», «M1 1AE», «CR2 6XH»)."""
    limpio = texto.strip().upper()
    return bool(re.fullmatch(
        r"[A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2}", limpio))


def es_zip_us(texto: str) -> bool:
    """Código postal estadounidense: 5 dígitos, opcionalmente +4 (ZIP+4)."""
    return bool(re.fullmatch(r"\d{5}(?:-\d{4})?", texto.strip()))


def es_telefono_uk(texto: str) -> bool:
    """Teléfono británico: +44 o 0 inicial y 10 dígitos nacionales."""
    limpio = re.sub(r"[\s.\-()]", "", texto)
    limpio = limpio.removeprefix("+44").removeprefix("0044")
    if not limpio.startswith("0"):
        limpio = "0" + limpio
    return bool(re.fullmatch(r"0\d{9,10}", limpio))


def es_telefono_us(texto: str) -> bool:
    """Teléfono norteamericano (NANP): 10 dígitos, con +1 opcional.

    Área y central empiezan por 2-9 (regla del plan de numeración), lo que
    descarta muchos números de serie que solo se parecen a un teléfono.
    """
    limpio = re.sub(r"[\s.\-()]", "", texto)
    limpio = limpio.removeprefix("+1").removeprefix("001")
    return bool(re.fullmatch(r"[2-9]\d{2}[2-9]\d{6}", limpio))
