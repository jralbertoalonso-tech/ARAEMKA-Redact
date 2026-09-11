"""Saneado común de paquetes Office Open XML (.docx y .xlsx).

Word y Excel son contenedores ZIP. Limpiar solo las propiedades que exponen
``python-docx`` u ``openpyxl`` deja fuera propiedades personalizadas, XML
personalizado, comentarios, revisiones eliminadas, enlaces externos y marcas
temporales del propio ZIP. Este módulo elimina esas fuentes de información sin
escribir nunca el documento en disco.
"""

from __future__ import annotations

import html
import io
import posixpath
import zipfile

from lxml import etree


_NS_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
_NS_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


def _parsear(datos: bytes):
    # Los endpoints de FastAPI pueden sanear varios documentos en paralelo;
    # cada parseo usa su propia instancia (los parsers de lxml no se comparten).
    parser = etree.XMLParser(resolve_entities=False, no_network=True, recover=False)
    return etree.fromstring(datos, parser)


def validar_paquete_ooxml(contenido: bytes, max_descomprimido: int = 500 * 1024 * 1024):
    """Rechaza ZIP dañados o desmesurados antes de abrirlos con Office libs."""
    with zipfile.ZipFile(io.BytesIO(contenido)) as paquete:
        total = sum(info.file_size for info in paquete.infolist())
        if total > max_descomprimido:
            raise ValueError("El documento Office es demasiado grande al descomprimirse.")
        if len(paquete.infolist()) > 100_000:
            raise ValueError("El documento Office contiene demasiados elementos.")


def _es_parte_privada(nombre: str) -> bool:
    """Partes no visibles que se eliminan por privacidad."""
    n = nombre.lower().lstrip("/")
    return (
        n.startswith("docprops/")
        or n.startswith("customxml/")
        or n.startswith("word/comments")
        or n.startswith("word/people")
        or n.startswith("word/printersettings/")
        or n.startswith("xl/comments")
        or n.startswith("xl/threadedcomments/")
        or n.startswith("xl/persons/")
        or n.startswith("xl/drawings/commentsdrawing")
        or n.startswith("xl/printersettings/")
        or n.endswith("/thumbnail.jpeg")
        or n.endswith("/thumbnail.jpg")
        or n.endswith("/thumbnail.png")
    )


def _origen_de_relaciones(nombre: str) -> str | None:
    """Convierte ``word/_rels/document.xml.rels`` en ``word/document.xml``."""
    n = nombre.lstrip("/")
    if n == "_rels/.rels":
        return None
    carpeta, archivo = posixpath.split(n)
    if not carpeta.endswith("/_rels") or not archivo.endswith(".rels"):
        return None
    base = carpeta[:-len("/_rels")]
    return posixpath.join(base, archivo[:-len(".rels")])


def _destino_relacion(origen: str | None, destino: str) -> str:
    if destino.startswith("/"):
        return posixpath.normpath(destino).lstrip("/")
    base = posixpath.dirname(origen) if origen else ""
    return posixpath.normpath(posixpath.join(base, destino)).lstrip("/")


def _serializar(raiz, original: bytes) -> bytes:
    return etree.tostring(
        raiz,
        encoding="UTF-8",
        xml_declaration=original.lstrip().startswith(b"<?xml"),
        standalone=None,
    )


def _sanear_relaciones(nombre: str, datos: bytes) -> tuple[bytes, set[str]]:
    """Quita relaciones a partes eliminadas y todos los destinos externos."""
    try:
        raiz = _parsear(datos)
    except etree.XMLSyntaxError:
        return datos, set()
    origen = _origen_de_relaciones(nombre)
    eliminados: set[str] = set()
    cambiado = False
    for relacion in list(raiz):
        destino = relacion.get("Target", "")
        externo = relacion.get("TargetMode", "").lower() == "external"
        privado = bool(destino) and _es_parte_privada(_destino_relacion(origen, destino))
        if externo or privado:
            if relacion.get("Id"):
                eliminados.add(relacion.get("Id"))
            raiz.remove(relacion)
            cambiado = True
    return (_serializar(raiz, datos) if cambiado else datos), eliminados


def _quitar_elemento(elemento):
    padre = elemento.getparent()
    if padre is None:
        return
    cola = elemento.tail
    anterior = elemento.getprevious()
    padre.remove(elemento)
    if cola:
        if anterior is not None:
            anterior.tail = (anterior.tail or "") + cola
        else:
            padre.text = (padre.text or "") + cola


def _desenvolver(elemento):
    """Elimina un contenedor XML conservando sus hijos visibles."""
    padre = elemento.getparent()
    if padre is None:
        return
    indice = padre.index(elemento)
    hijos = list(elemento)
    for hijo in hijos:
        elemento.remove(hijo)
        padre.insert(indice, hijo)
        indice += 1
    if elemento.tail:
        if hijos:
            hijos[-1].tail = (hijos[-1].tail or "") + elemento.tail
        elif indice:
            previo = padre[indice - 1]
            previo.tail = (previo.tail or "") + elemento.tail
        else:
            padre.text = (padre.text or "") + elemento.tail
    padre.remove(elemento)


def _sanear_xml_word(datos: bytes) -> bytes:
    """Elimina revisiones ocultas y marcadores personales de Word."""
    try:
        raiz = _parsear(datos)
    except etree.XMLSyntaxError:
        return datos
    ns = {"w": _NS_W}
    cambiado = False

    # El texto de una revisión eliminada sigue dentro del .docx aunque Word no
    # lo muestre. Las inserciones aceptadas sí se conservan como texto normal.
    for consulta in (".//w:del", ".//w:moveFrom"):
        for elemento in raiz.xpath(consulta, namespaces=ns):
            _quitar_elemento(elemento)
            cambiado = True
    for consulta in (".//w:ins", ".//w:moveTo", ".//w:customXml"):
        for elemento in raiz.xpath(consulta, namespaces=ns):
            _desenvolver(elemento)
            cambiado = True

    for consulta in (
        ".//w:commentRangeStart", ".//w:commentRangeEnd", ".//w:commentReference",
        ".//w:docVars", ".//w:dataBinding", ".//w:trackRevisions",
    ):
        for elemento in raiz.xpath(consulta, namespaces=ns):
            _quitar_elemento(elemento)
            cambiado = True

    # rsid, autor y fecha de revisión permiten identificar al editor incluso
    # cuando ya no queda una propiedad de documento convencional.
    for elemento in raiz.iter():
        for atributo in list(elemento.attrib):
            local = etree.QName(atributo).localname.lower()
            if local.startswith("rsid") or local in {"author", "date", "initials"}:
                del elemento.attrib[atributo]
                cambiado = True

    return _serializar(raiz, datos) if cambiado else datos


def _quitar_ids_relacion(datos: bytes, ids: set[str]) -> bytes:
    """Quita referencias XML a relaciones externas o eliminadas."""
    if not ids:
        return datos
    try:
        raiz = _parsear(datos)
    except etree.XMLSyntaxError:
        return datos
    cambiado = False
    for elemento in list(raiz.iter()):
        quitar = False
        for atributo, valor in list(elemento.attrib.items()):
            if valor in ids and etree.QName(atributo).namespace == _NS_R:
                del elemento.attrib[atributo]
                cambiado = True
                quitar = etree.QName(elemento).localname in {"legacyDrawing", "legacyDrawingHF"}
        if quitar:
            _quitar_elemento(elemento)
    return _serializar(raiz, datos) if cambiado else datos


def _sanear_content_types(datos: bytes) -> bytes:
    try:
        raiz = _parsear(datos)
    except etree.XMLSyntaxError:
        return datos
    cambiado = False
    for elemento in list(raiz):
        parte = (elemento.get("PartName") or "").lstrip("/")
        if parte and _es_parte_privada(parte):
            raiz.remove(elemento)
            cambiado = True
    return _serializar(raiz, datos) if cambiado else datos


def limpiar_metadatos_ooxml(contenido: bytes) -> bytes:
    """Devuelve un paquete Office sin propiedades ni contenido oculto común.

    Además de las propiedades, elimina comentarios, XML personalizado, texto de
    revisiones borradas, destinos de enlaces externos y ajustes de impresora.
    Las fechas internas de cada entrada ZIP se normalizan para no conservar la
    cronología del equipo creador.
    """
    validar_paquete_ooxml(contenido)
    origen = io.BytesIO(contenido)
    salida = io.BytesIO()
    with zipfile.ZipFile(origen) as entrada:
        nombres = [i.filename for i in entrada.infolist()]
        datos_por_nombre = {nombre: entrada.read(nombre) for nombre in nombres}

    # Primero se calculan los r:id que desaparecerán; después se limpian en el
    # XML de origen para no dejar referencias colgantes.
    ids_por_origen: dict[str, set[str]] = {}
    for nombre in nombres:
        if nombre.endswith(".rels") and not _es_parte_privada(nombre):
            datos, ids = _sanear_relaciones(nombre, datos_por_nombre[nombre])
            datos_por_nombre[nombre] = datos
            origen_rel = _origen_de_relaciones(nombre)
            if origen_rel and ids:
                ids_por_origen.setdefault(origen_rel, set()).update(ids)

    with zipfile.ZipFile(salida, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as destino:
        for nombre in nombres:
            if nombre.endswith("/") or _es_parte_privada(nombre):
                continue
            datos = datos_por_nombre[nombre]
            if nombre == "[Content_Types].xml":
                datos = _sanear_content_types(datos)
            if nombre.startswith("word/") and nombre.endswith(".xml"):
                datos = _sanear_xml_word(datos)
            if nombre in ids_por_origen:
                datos = _quitar_ids_relacion(datos, ids_por_origen[nombre])

            info = zipfile.ZipInfo(nombre, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o600 << 16
            destino.writestr(info, datos)
    return salida.getvalue()


def buscar_textos_en_paquete(contenido: bytes, textos: list[str]) -> list[str]:
    """Busca textos aprobados también en XML, relaciones y partes binarias."""
    candidatos = [t.strip() for t in textos if t and t.strip()]
    if not candidatos:
        return []
    encontrados: set[str] = set()
    with zipfile.ZipFile(io.BytesIO(contenido)) as paquete:
        for info in paquete.infolist():
            if info.is_dir() or info.file_size > 100 * 1024 * 1024:
                continue
            datos = paquete.read(info.filename)
            texto_plano = None
            if info.filename.lower().endswith((".xml", ".rels", ".txt")):
                texto_plano = html.unescape(datos.decode("utf-8", errors="ignore")).casefold()
            for candidato in candidatos:
                if candidato in encontrados:
                    continue
                plegado = candidato.casefold()
                if texto_plano is not None and plegado in texto_plano:
                    encontrados.add(candidato)
                    continue
                for codificacion in ("utf-8", "utf-16le", "utf-16be"):
                    try:
                        aguja = candidato.encode(codificacion)
                    except UnicodeEncodeError:
                        continue
                    if aguja and aguja in datos:
                        encontrados.add(candidato)
                        break
    return [t for t in candidatos if t in encontrados]
