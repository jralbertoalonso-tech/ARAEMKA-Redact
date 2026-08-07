"""Desplazamiento consistente de fechas y rangos etarios (Fase 5).

Dos alternativas a la redacción pura, pensadas para conservar la utilidad
clínica del documento:

- **Desplazar fechas**: todas las fechas del documento se mueven el MISMO número
  aleatorio de días (p. ej. +117). La cronología se conserva (los intervalos
  entre ingreso, pruebas y alta no cambian), pero las fechas reales desaparecen.
  El desplazamiento se genera por documento y NUNCA se guarda en la auditoría
  (permitiría deshacer la anonimización).

- **Rango etario**: la edad exacta («47 años») se sustituye por su banda
  quinquenal («45-49 años»), práctica habitual en publicación científica.

Si una fecha no se puede interpretar con seguridad, se devuelve None y el
llamador la redacta del todo: ante la duda, la opción más conservadora.
"""

import re
from datetime import date, timedelta

MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
_NUM_MES = {m: i + 1 for i, m in enumerate(MESES)}
_NUM_MES["setiembre"] = 9  # variante admitida

_RE_NUMERICA = re.compile(r"^(\d{1,2})([/\-.])(\d{1,2})\2(\d{4}|\d{2})$")
_RE_ISO = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")
_RE_TEXTUAL = re.compile(
    r"^(\d{1,2})\s+de\s+([a-záé]+)\s+(?:de\s+|del\s+)?(\d{4})$", re.IGNORECASE)
_RE_MES_ANIO = re.compile(r"^([a-záé]+)\s+(?:de\s+|del\s+)?(\d{4})$", re.IGNORECASE)

# ── Inglés (Reino Unido y EE. UU.) ──────────────────────────────────────────
# Solo se usa en documentos en inglés (idioma="en"); el camino español no
# cambia. Los meses se escriben con letra en el resultado para no reintroducir
# la ambigüedad día/mes de los formatos numéricos.
MESES_EN = ["january", "february", "march", "april", "may", "june", "july",
            "august", "september", "october", "november", "december"]
_NUM_MES_EN = {m: i + 1 for i, m in enumerate(MESES_EN)}
# Abreviaturas habituales
for _full, _ab in zip(MESES_EN, ["jan", "feb", "mar", "apr", "may", "jun", "jul",
                                 "aug", "sep", "oct", "nov", "dec"]):
    _NUM_MES_EN[_ab] = _NUM_MES_EN[_full]
_NUM_MES_EN["sept"] = 9  # variante de 4 letras

# «March 3, 2024» / «Mar 3 2024» / «March 3rd, 2024»  (mes día año)
_RE_EN_MES_DIA = re.compile(
    r"^([A-Za-z]+)\.?\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})$", re.IGNORECASE)
# «3 March 2024» / «3rd of March, 2024» / «3 Mar 2024»  (día mes año)
_RE_EN_DIA_MES = re.compile(
    r"^(\d{1,2})(?:st|nd|rd|th)?\s+(?:of\s+)?([A-Za-z]+)\.?,?\s+(\d{4})$", re.IGNORECASE)
# «January 2024» / «Jan 2024»  (mes año, sin día)
_RE_EN_MES_ANIO = re.compile(r"^([A-Za-z]+)\.?\s+(\d{4})$", re.IGNORECASE)


def _anio_completo(anio_txt: str) -> int:
    """Expande un año de 2 cifras (78→1978, 24→2024) o deja el de 4 tal cual."""
    n = int(anio_txt)
    if len(anio_txt) == 2:
        return 2000 + n if n <= 49 else 1900 + n
    return n


def _mes_en_salida(indice_mes: int, token_original: str) -> str:
    """Nombre del mes para el resultado, respetando si venía abreviado."""
    completo = MESES_EN[indice_mes - 1].capitalize()
    limpio = token_original.strip(".").lower()
    if limpio in MESES_EN:            # venía completo
        return completo
    return completo[:3]               # venía abreviado → «Mar», «Sep»…


def _desplazar_en(texto: str, delta_dias: int) -> str | None:
    """Desplaza una fecha en inglés. None si no se puede interpretar SIN adivinar.

    Las fechas numéricas (03/04/2024) solo se desplazan cuando se delatan solas
    (algún número > 12); si ambos son ≤ 12 son genuinamente ambiguas entre el
    formato británico (día/mes) y el estadounidense (mes/día) y se devuelve None
    para que se tachen: nunca se adivina el orden.
    """
    # ISO: inequívoco
    m = _RE_ISO.match(texto)
    if m:
        f = _fecha_segura(int(m[1]), int(m[2]), int(m[3]))
        if not f:
            return None
        return (f + timedelta(days=delta_dias)).isoformat()

    # Mes con letra, día antes o después: inequívoco
    for patron, orden in ((_RE_EN_MES_DIA, "md"), (_RE_EN_DIA_MES, "dm")):
        m = patron.match(texto)
        if not m:
            continue
        tok_mes = m[1] if orden == "md" else m[2]
        dia = int(m[2] if orden == "md" else m[1])
        mes = _NUM_MES_EN.get(tok_mes.strip(".").lower())
        if not mes:
            return None
        f = _fecha_segura(int(m[3]), mes, dia)
        if not f:
            return None
        f += timedelta(days=delta_dias)
        nombre = _mes_en_salida(f.month, tok_mes)
        return f"{nombre} {f.day}, {f.year}" if orden == "md" else f"{f.day} {nombre} {f.year}"

    # Mes y año, sin día: se toma el día 15 de referencia (como en español)
    m = _RE_EN_MES_ANIO.match(texto)
    if m:
        mes = _NUM_MES_EN.get(m[1].strip(".").lower())
        if mes:
            f = _fecha_segura(int(m[2]), mes, 15)
            if f:
                f += timedelta(days=delta_dias)
                return f"{_mes_en_salida(f.month, m[1])} {f.year}"
        return None

    # Numérico: solo si se delata solo (algún componente > 12)
    m = _RE_NUMERICA.match(texto)
    if m:
        a, sep, b, anio = int(m[1]), m[2], int(m[3]), m[4]
        anio_n = _anio_completo(anio)
        if a > 12 and b <= 12:          # día/mes (británico) inequívoco
            dia, mes = a, b
        elif b > 12 and a <= 12:        # mes/día (estadounidense) inequívoco
            dia, mes = b, a
        else:
            return None                 # ambiguo (ambos ≤ 12) o imposible → tachar
        f = _fecha_segura(anio_n, mes, dia)
        if not f:
            return None
        f += timedelta(days=delta_dias)
        # Reconstruye respetando la posición original de cada número
        n_dia = f"{f.day:02d}"
        n_mes = f"{f.month:02d}"
        pa, pb = (n_dia, n_mes) if (a > 12) else (n_mes, n_dia)
        anio_txt = f"{f.year % 100:02d}" if len(anio) == 2 else f"{f.year}"
        return f"{pa}{sep}{pb}{sep}{anio_txt}"

    return None


def desplazar_fecha(texto: str, delta_dias: int, idioma: str = "es") -> str | None:
    """Devuelve el texto de la fecha desplazada `delta_dias`, conservando el
    formato original. None si no se puede interpretar con seguridad.

    En documentos en inglés (`idioma="en"`) usa los formatos ingleses; el camino
    español queda intacto."""
    texto = texto.strip()

    if idioma == "en":
        return _desplazar_en(texto, delta_dias)

    m = _RE_NUMERICA.match(texto)
    if m:
        dia, sep, mes, anio = int(m[1]), m[2], int(m[3]), m[4]
        anio_n = int(anio) + (2000 if len(anio) == 2 and int(anio) <= 49 else
                              1900 if len(anio) == 2 else 0)
        f = _fecha_segura(anio_n, mes, dia)
        if not f:
            return None
        f += timedelta(days=delta_dias)
        anio_txt = f"{f.year % 100:02d}" if len(anio) == 2 else f"{f.year}"
        return f"{f.day:02d}{sep}{f.month:02d}{sep}{anio_txt}"

    m = _RE_ISO.match(texto)
    if m:
        f = _fecha_segura(int(m[1]), int(m[2]), int(m[3]))
        if not f:
            return None
        f += timedelta(days=delta_dias)
        return f.isoformat()

    m = _RE_TEXTUAL.match(texto)
    if m:
        mes = _NUM_MES.get(m[2].lower())
        if not mes:
            return None
        f = _fecha_segura(int(m[3]), mes, int(m[1]))
        if not f:
            return None
        f += timedelta(days=delta_dias)
        return f"{f.day} de {MESES[f.month - 1]} de {f.year}"

    m = _RE_MES_ANIO.match(texto)
    if m:
        mes = _NUM_MES.get(m[1].lower())
        if not mes:
            return None
        # Sin día concreto: se toma el día 15 como referencia para el desplazamiento
        f = _fecha_segura(int(m[2]), mes, 15)
        if not f:
            return None
        f += timedelta(days=delta_dias)
        return f"{MESES[f.month - 1]} de {f.year}"

    return None


def _fecha_segura(anio: int, mes: int, dia: int) -> date | None:
    try:
        return date(anio, mes, dia)
    except ValueError:
        return None


# ── rangos etarios ─────────────────────────────────────────────────────────

_RE_EDAD_ANIOS = re.compile(r"^(\d{1,3})\s+años(\s+de\s+edad)?$", re.IGNORECASE)
_RE_EDAD_MESES = re.compile(r"^(\d{1,2})\s+meses(\s+de\s+edad)?$", re.IGNORECASE)

# Inglés: «47 years old», «47 years», «aged 47», «47-year-old», «8 months old»
_RE_EDAD_ANIOS_EN = re.compile(
    r"^(?:aged\s+)?(\d{1,3})[\s\-]*years?(?:[\s\-]*old)?$", re.IGNORECASE)
_RE_EDAD_ANIOS_EN2 = re.compile(r"^(\d{1,3})[\s\-]*year[\s\-]*old$", re.IGNORECASE)
_RE_EDAD_AGED_EN = re.compile(r"^aged\s+(\d{1,3})$", re.IGNORECASE)   # «aged 47» sin «years»
_RE_EDAD_MESES_EN = re.compile(
    r"^(\d{1,2})[\s\-]*months?(?:[\s\-]*old)?$", re.IGNORECASE)


def rango_etario(texto: str, idioma: str = "es") -> str | None:
    """«47 años» → «45-49 años»; «8 meses de edad» → «menor de 1 año».

    En inglés: «47 years old» → «45-49 years»; «8 months old» → «under 1 year».
    Bandas quinquenales estándar (0-4, 5-9, …, 85 o más). None si el texto no
    es una edad reconocible."""
    texto = texto.strip()
    if idioma == "en":
        return _rango_etario_en(texto)

    def banda(edad_anios, sufijo):
        if edad_anios >= 85:
            return f"85 o más años{sufijo}"
        base = (edad_anios // 5) * 5
        return f"{base}-{base + 4} años{sufijo}"

    m = _RE_EDAD_MESES.match(texto)
    if m:
        meses = int(m[1])
        sufijo = m[2] or ""
        # «8 meses» es menor de 1 año; pero «18 meses» son 1,5 años y debe
        # caer en su banda etaria, no marcarse como «menor de 1 año».
        if meses < 12:
            return f"menor de 1 año{sufijo}"
        return banda(meses // 12, sufijo)

    m = _RE_EDAD_ANIOS.match(texto)
    if m:
        return banda(int(m[1]), m[2] or "")

    return None


def _rango_etario_en(texto: str) -> str | None:
    """Versión inglesa: «47 years old» → «45-49 years»; «8 months old» → «under 1 year»."""
    def banda(edad_anios):
        if edad_anios >= 85:
            return "85 or older"
        base = (edad_anios // 5) * 5
        return f"{base}-{base + 4} years"

    m = _RE_EDAD_MESES_EN.match(texto)
    if m:
        meses = int(m[1])
        return "under 1 year" if meses < 12 else banda(meses // 12)

    m = (_RE_EDAD_ANIOS_EN.match(texto) or _RE_EDAD_ANIOS_EN2.match(texto)
         or _RE_EDAD_AGED_EN.match(texto))
    return banda(int(m[1])) if m else None


def es_edad(texto: str, idioma: str = "es") -> bool:
    """True si el texto detectado es una edad (y no una fecha de nacimiento)."""
    t = texto.strip()
    if idioma == "en":
        return bool(_RE_EDAD_ANIOS_EN.match(t) or _RE_EDAD_ANIOS_EN2.match(t)
                    or _RE_EDAD_AGED_EN.match(t) or _RE_EDAD_MESES_EN.match(t))
    return bool(_RE_EDAD_ANIOS.match(t) or _RE_EDAD_MESES.match(t))
