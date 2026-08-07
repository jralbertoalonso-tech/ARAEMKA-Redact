"""Detección automática del idioma de un documento (español vs. inglés).

No añade dependencias: cuenta palabras funcionales muy frecuentes y exclusivas
de cada idioma (artículos, preposiciones, conjunciones). Para el único par que
nos interesa —español frente a inglés— este método es rápido, funciona sin red
y acierta de sobra incluso con pocas frases.

Ante la duda (documento muy corto, cifras sueltas, empate), devuelve "es": es
el idioma principal de la aplicación y su motor es el más completo, así que es
la opción más conservadora frente a fugas.
"""

import re

# Palabras muy frecuentes y prácticamente exclusivas de cada idioma. Se evitan
# las ambiguas entre ambos ("no", "en", "un" existen o se confunden).
_ES = {
    "el", "la", "los", "las", "un", "una", "unos", "unas", "de", "del", "y",
    "que", "en", "con", "por", "para", "su", "sus", "se", "al", "lo", "como",
    "más", "pero", "sus", "le", "ya", "o", "este", "esta", "son", "es", "está",
    "días", "años", "según", "sobre", "entre", "hasta", "desde", "cuando",
    "paciente", "señor", "señora", "doña", "fecha", "nombre", "domicilio",
}
_EN = {
    "the", "a", "an", "of", "and", "to", "in", "is", "are", "was", "were",
    "for", "with", "on", "at", "by", "from", "this", "that", "these", "those",
    "it", "as", "be", "has", "have", "had", "not", "but", "or", "which", "who",
    "shall", "will", "patient", "name", "date", "address", "hereby", "between",
}

_TOKEN = re.compile(r"[a-záéíóúñü]+", re.IGNORECASE)


def detectar_idioma(texto: str) -> str:
    """Devuelve "es" o "en" según qué palabras funcionales predominan."""
    if not texto:
        return "es"
    # Basta con una muestra: las primeras ~4000 palabras marcan el idioma y así
    # no recorremos historias clínicas de 40 páginas enteras.
    palabras = _TOKEN.findall(texto.lower())[:4000]
    if not palabras:
        return "es"

    es = sum(1 for p in palabras if p in _ES)
    en = sum(1 for p in palabras if p in _EN)

    # La tilde y la ñ son señal fuerte de español aunque haya poco texto.
    if re.search(r"[áéíóúñ¿¡]", texto):
        es += 3

    # Empate o casi empate → español (opción conservadora).
    if en > es * 1.15:
        return "en"
    return "es"
