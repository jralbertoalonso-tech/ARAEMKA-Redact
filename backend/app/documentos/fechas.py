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


def desplazar_fecha(texto: str, delta_dias: int) -> str | None:
    """Devuelve el texto de la fecha desplazada `delta_dias`, conservando el
    formato original. None si no se puede interpretar con seguridad."""
    texto = texto.strip()

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


def rango_etario(texto: str) -> str | None:
    """«47 años» → «45-49 años»; «8 meses de edad» → «menor de 1 año».

    Bandas quinquenales estándar (0-4, 5-9, …, 85 o más). None si el texto no
    es una edad reconocible."""
    texto = texto.strip()

    m = _RE_EDAD_MESES.match(texto)
    if m:
        sufijo = m[2] or ""
        return f"menor de 1 año{sufijo}"

    m = _RE_EDAD_ANIOS.match(texto)
    if m:
        edad = int(m[1])
        sufijo = m[2] or ""
        if edad >= 85:
            return f"85 o más años{sufijo}"
        base = (edad // 5) * 5
        return f"{base}-{base + 4} años{sufijo}"

    return None


def es_edad(texto: str) -> bool:
    """True si el texto detectado es una edad (y no una fecha de nacimiento)."""
    t = texto.strip()
    return bool(_RE_EDAD_ANIOS.match(t) or _RE_EDAD_MESES.match(t))
