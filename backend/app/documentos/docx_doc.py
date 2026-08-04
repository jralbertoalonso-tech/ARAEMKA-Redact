"""Manejo de documentos Word (.docx): extracción por bloques y redacción por sustitución.

En .docx la redacción destructiva consiste en SUSTITUIR el texto detectado por
bloques █ dentro del XML del documento: el texto original deja de existir en el
archivo. Se recorren párrafos, tablas, cabeceras y pies de página.

Limitación documentada (MVP): al redactar un párrafo se conserva el formato del
párrafo y de su primera secuencia de texto, pero se pierden los cambios de
formato internos (p. ej., una palabra en negrita a mitad de frase). El texto no
afectado del resto del documento no se toca.

Los .doc antiguos (Word 97-2003) no son compatibles: la API los rechaza con un
mensaje que sugiere guardarlos como .docx.
"""

import copy
import io

from docx import Document

CARACTER_REDACCION = "█"


class BloqueDocx:
    """Un párrafo (de cuerpo, tabla, cabecera o pie) con su texto."""

    def __init__(self, indice: int, texto: str, origen: str):
        self.indice = indice   # id estable dentro del documento
        self.texto = texto
        self.origen = origen   # cuerpo | tabla | cabecera | pie


def _parrafos_del_documento(doc) -> list:
    """Todos los párrafos en orden: cuerpo, tablas, cabeceras y pies."""
    parrafos = []

    def de_tabla(tabla):
        for fila in tabla.rows:
            for celda in fila.cells:
                for p in celda.paragraphs:
                    parrafos.append((p, "tabla"))
                for t in celda.tables:  # tablas anidadas
                    de_tabla(t)

    for p in doc.paragraphs:
        parrafos.append((p, "cuerpo"))
    for tabla in doc.tables:
        de_tabla(tabla)
    for seccion in doc.sections:
        for p in seccion.header.paragraphs:
            parrafos.append((p, "cabecera"))
        for tabla in seccion.header.tables:
            de_tabla(tabla)
        for p in seccion.footer.paragraphs:
            parrafos.append((p, "pie"))
        for tabla in seccion.footer.tables:
            de_tabla(tabla)
    return parrafos


class DocumentoDocx:
    """Un .docx cargado en memoria, listo para analizar y redactar."""

    def __init__(self, contenido: bytes):
        self.contenido = contenido
        self.bloques: list[BloqueDocx] = []
        self._extraer()

    def _extraer(self):
        doc = Document(io.BytesIO(self.contenido))
        for i, (p, origen) in enumerate(_parrafos_del_documento(doc)):
            self.bloques.append(BloqueDocx(i, p.text, origen))

    # ── redacción ──────────────────────────────────────────────────────────
    def redactar(self, spans_por_bloque: dict[int, list[tuple]]) -> bytes:
        """Sustituye los intervalos indicados y devuelve el .docx.

        `spans_por_bloque`: {índice_de_bloque: [(inicio, fin) | (inicio, fin,
        texto_nuevo), …]} con offsets sobre el texto del bloque. Sin texto nuevo
        el intervalo se sustituye por █; con él (fechas desplazadas, rangos
        etarios) se escribe ese texto — el original desaparece igualmente del
        archivo. También limpia las propiedades del documento (autor, último
        editor…), que suelen contener nombres reales.
        """
        doc = Document(io.BytesIO(self.contenido))
        parrafos = _parrafos_del_documento(doc)

        for indice, spans in spans_por_bloque.items():
            if not (0 <= indice < len(parrafos)) or not spans:
                continue
            parrafo, _ = parrafos[indice]
            original = parrafo.text
            # Construye el texto redactado sustituyendo cada intervalo
            trozos, cursor = [], 0
            for span in sorted(spans):
                ini, fin = max(0, span[0]), min(len(original), span[1])
                reemplazo = span[2] if len(span) > 2 else None
                if ini < cursor:
                    ini = cursor
                if ini >= fin:
                    continue
                trozos.append(original[cursor:ini])
                trozos.append(reemplazo if reemplazo is not None
                              else CARACTER_REDACCION * max(4, fin - ini))
                cursor = fin
            trozos.append(original[cursor:])
            nuevo_texto = "".join(trozos)

            # Sustituye el contenido conservando el formato de la primera
            # secuencia (fuente, tamaño, negrita del inicio del párrafo).
            if parrafo.runs:
                primera = parrafo.runs[0]
                primera.text = nuevo_texto
                for run in parrafo.runs[1:]:
                    run.text = ""
            else:
                parrafo.add_run(nuevo_texto)

        # Limpieza de metadatos del archivo
        nucleo = doc.core_properties
        nucleo.author = ""
        nucleo.last_modified_by = ""
        nucleo.title = ""
        nucleo.subject = ""
        nucleo.comments = ""
        nucleo.category = ""
        nucleo.keywords = ""

        salida = io.BytesIO()
        doc.save(salida)
        return salida.getvalue()

    def contiene_texto_oculto(self, textos: list[str]) -> list[str]:
        """Comprueba si alguno de los textos sigue presente (verificación)."""
        restante = "\n".join(b.texto for b in self.bloques).lower()
        return [t for t in textos if t.strip() and t.strip().lower() in restante]
