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

import io

from docx import Document
from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph

from .ooxml import buscar_textos_en_paquete, limpiar_metadatos_ooxml

CARACTER_REDACCION = "█"


class BloqueDocx:
    """Un párrafo (de cuerpo, tabla, cabecera o pie) con su texto."""

    def __init__(self, indice: int, texto: str, origen: str):
        self.indice = indice   # id estable dentro del documento
        self.texto = texto
        self.origen = origen   # cuerpo | tabla | cabecera | pie


def _parrafos_del_documento(doc) -> list:
    """TODOS los párrafos del documento, en orden y sin duplicados.

    Recorre el XML buscando cada elemento `w:p` (párrafo) allí donde esté:
    cuerpo, tablas (incluidas anidadas), cabeceras, pies, **cuadros de texto**
    (`w:txbxContent`) y **controles de contenido** (`w:sdt`). Esto cubre huecos
    de la API estructurada de python-docx, que no expone los cuadros de texto y
    que DUPLICA las celdas combinadas de tabla. La deduplicación por identidad
    del elemento evita que una celda combinada (o una cabecera vinculada) se
    procese dos veces, lo que corrompía el texto al redactar.
    """
    parrafos = []
    vistos = set()

    def anadir(contenedor, origen):
        if contenedor is None:
            return
        for p_el in contenedor.iter(qn("w:p")):
            if id(p_el) in vistos:
                continue
            vistos.add(id(p_el))
            parrafos.append((Paragraph(p_el, doc), origen))

    anadir(doc.element.body, "cuerpo")
    for seccion in doc.sections:
        anadir(seccion.header._element, "cabecera")
        anadir(seccion.footer._element, "pie")
        # Cabeceras/pies de primera página y páginas pares, si existen
        for extra in (getattr(seccion, "first_page_header", None),
                      getattr(seccion, "even_page_header", None),
                      getattr(seccion, "first_page_footer", None),
                      getattr(seccion, "even_page_footer", None)):
            if extra is not None:
                anadir(extra._element, "cabecera")
    return parrafos


def _elementos_texto(parrafo):
    """Todos los `w:t` del párrafo, incluidos los de dentro de hipervínculos."""
    return parrafo._p.findall(".//" + qn("w:t"))


class DocumentoDocx:
    """Un .docx cargado en memoria, listo para analizar y redactar."""

    def __init__(self, contenido: bytes):
        # Se trabaja sobre una copia saneada en RAM. Así las inserciones
        # controladas pasan a ser texto normal, las eliminaciones antiguas no
        # se analizan como si siguieran visibles y comentarios/propiedades no
        # viajan siquiera hasta la copia resultante.
        self.contenido = limpiar_metadatos_ooxml(contenido)
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

            # Sustituye el contenido a nivel de XML: pone TODO el texto redactado
            # en el primer elemento de texto y VACÍA el resto —incluidos los que
            # están dentro de hipervínculos, que `parrafo.runs` no toca y que
            # dejaban el dato original (típicamente un email) en el archivo.
            t_elems = _elementos_texto(parrafo)
            if t_elems:
                t_elems[0].text = nuevo_texto
                t_elems[0].set(qn("xml:space"), "preserve")
                for t in t_elems[1:]:
                    t.text = ""
            else:
                parrafo.add_run(nuevo_texto)

            # Neutraliza los hipervínculos del párrafo redactado: quita la
            # referencia (r:id) para que la URL —que puede contener el dato,
            # p. ej. «mailto:nombre@hospital.es»— deje de estar enlazada.
            for hl in parrafo._p.findall(".//" + qn("w:hyperlink")):
                if qn("r:id") in hl.attrib:
                    del hl.attrib[qn("r:id")]

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
        # python-docx vuelve a crear algunas propiedades del paquete al
        # guardar. Se sanea una segunda vez para cubrir también propiedades
        # personalizadas, revisiones, comentarios y enlaces externos.
        return limpiar_metadatos_ooxml(salida.getvalue())

    def contiene_texto_oculto(self, textos: list[str]) -> list[str]:
        """Comprueba texto visible y también partes internas del paquete."""
        restante = "\n".join(b.texto for b in self.bloques).casefold()
        visibles = [t for t in textos if t.strip() and t.strip().casefold() in restante]
        internos = buscar_textos_en_paquete(self.contenido, textos)
        return list(dict.fromkeys(visibles + internos))
