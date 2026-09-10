"""Manejo de PDF: extracción posicionada, OCR de escaneados y redacción destructiva.

La redacción usa las «redaction annotations» de PyMuPDF (`apply_redactions`),
que ELIMINAN el contenido bajo el rectángulo — no lo tapan. En un PDF con texto
se borra el texto de la capa; en un PDF escaneado (o una imagen) se borran los
PÍXELES de la imagen. En ambos casos el dato original desaparece del archivo: no
se puede recuperar copiando/pegando ni quitando el rectángulo negro.

Fase 2: los PDF escaneados y las imágenes ya NO se rechazan. Se procesan con OCR
local (Tesseract español, ver `ocr.py`), que reconoce cada palabra y su posición
para poder detectarla y redactarla.
"""

import io
import unicodedata

import fitz  # PyMuPDF
from PIL import Image

from . import ocr

# Un PDF escaneado a esta resolución da buen OCR sin disparar el tiempo/memoria.
DPI_OCR = 220

# Franjas de la página donde una imagen se considera membrete (logo/cabecera/pie).
FRANJA_CABECERA = 0.20   # 20 % superior
FRANJA_PIE = 0.12        # 12 % inferior


class PaginaPdf:
    """Texto de una página + posición (rectángulo) de cada palabra."""

    def __init__(self, numero: int, ancho: float, alto: float):
        self.numero = numero          # 0-index
        self.ancho = ancho            # puntos PDF
        self.alto = alto
        self.texto = ""               # texto reconstruido palabra a palabra
        # por cada palabra: (offset_inicio, offset_fin, rect, clave_de_línea)
        self.palabras: list[tuple[int, int, fitz.Rect, tuple]] = []
        self.por_ocr = False          # True si el texto vino de OCR, no de la capa
        self.area_imagen_rel = 0.0    # fracción de la página cubierta por imágenes

    def cargar_palabras(self, palabras: list[tuple[str, fitz.Rect, tuple]]):
        """Reconstruye `texto` y `palabras` (con offsets) a partir de (texto, rect, línea)."""
        trozos: list[str] = []
        offset = 0
        for palabra, rect, linea in palabras:
            palabra = unicodedata.normalize("NFC", palabra)
            if trozos:
                offset += 1  # espacio separador entre palabras
            inicio = offset
            offset += len(palabra)
            trozos.append(palabra)
            self.palabras.append((inicio, offset, fitz.Rect(rect), linea))
        self.texto = " ".join(trozos)


class DocumentoPdf:
    """Un PDF cargado en memoria, listo para analizar y redactar."""

    def __init__(self, contenido: bytes):
        self.contenido = contenido
        self.paginas: list[PaginaPdf] = []
        self.ocr_aplicado = False
        self._extraer()

    # ── extracción de la capa de texto ─────────────────────────────────────
    def _extraer(self):
        with fitz.open(stream=self.contenido, filetype="pdf") as doc:
            if doc.needs_pass:
                raise ValueError("El PDF está protegido con contraseña.")
            for num, page in enumerate(doc):
                pag = PaginaPdf(num, page.rect.width, page.rect.height)
                palabras = [
                    (palabra, fitz.Rect(x0, y0, x1, y1), (bloque, linea))
                    # sort=True ordena por posición de lectura (arriba→abajo, izq→dcha)
                    for x0, y0, x1, y1, palabra, bloque, linea, _ in page.get_text("words", sort=True)
                ]
                pag.cargar_palabras(palabras)
                pag.area_imagen_rel = self._cobertura_imagen(page)
                self.paginas.append(pag)

    @staticmethod
    def _cobertura_imagen(page) -> float:
        """Fracción de la página cubierta por la imagen más grande (0-1)."""
        area_pagina = page.rect.width * page.rect.height
        if area_pagina <= 0:
            return 0.0
        mayor = 0.0
        try:
            for info in page.get_image_info():
                b = info.get("bbox")
                if b:
                    r = fitz.Rect(b)
                    mayor = max(mayor, abs(r.width * r.height))
        except Exception:
            return 0.0
        return min(1.0, mayor / area_pagina)

    @property
    def tiene_texto(self) -> bool:
        """False si NINGUNA página tiene capa de texto útil (PDF escaneado)."""
        total = sum(len(p.texto.strip()) for p in self.paginas if not p.por_ocr)
        return total >= 20

    def paginas_sin_texto(self) -> list[int]:
        """Números de página que necesitan OCR.

        Incluye las páginas sin capa de texto (escaneadas puras) y también las
        que están DOMINADAS por una imagen (escaneo) pero llevan encima un poco
        de texto digital —un sello, una firma, «Página X de Y»—: antes ese texto
        superaba el umbral y la página se saltaba el OCR, dejando sin anonimizar
        todos los datos que hay dentro de la imagen escaneada (fuga silenciosa).
        """
        objetivo = []
        for p in self.paginas:
            n = len(p.texto.strip())
            if n < 15:
                objetivo.append(p.numero)
            elif p.area_imagen_rel > 0.55 and n < 600:
                objetivo.append(p.numero)  # escaneo con sello/firma de texto
        return objetivo

    # ── OCR de las páginas escaneadas ──────────────────────────────────────
    def aplicar_ocr(self, solo_paginas: list[int] | None = None) -> int:
        """Reconoce con OCR el texto de las páginas escaneadas.

        Renderiza cada página a imagen, la pasa por Tesseract y guarda las
        palabras con su posición (convertida de píxeles a puntos PDF). Devuelve
        cuántas páginas se han procesado. Lanza `ocr.OcrNoDisponible` si falta
        Tesseract.
        """
        objetivo = set(solo_paginas if solo_paginas is not None else self.paginas_sin_texto())
        if not objetivo:
            return 0

        escala = 72.0 / DPI_OCR  # factor de píxel de imagen → punto PDF
        procesadas = 0
        with fitz.open(stream=self.contenido, filetype="pdf") as doc:
            for pag in self.paginas:
                if pag.numero not in objetivo:
                    continue
                page = doc[pag.numero]
                pix = page.get_pixmap(dpi=DPI_OCR)
                imagen = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
                palabras_px = ocr.palabras_de_imagen(imagen)
                # El pixmap se renderiza en la orientación VISIBLE (con la
                # rotación aplicada). Para que la redacción caiga en el sitio
                # correcto, las cajas se llevan al sistema de coordenadas real
                # de la página con la matriz de des-rotación (identidad si
                # /Rotate == 0). Sin esto, en páginas giradas la redacción de
                # píxeles no tapaba el dato → fuga.
                deroto = page.derotation_matrix
                palabras = []
                for texto, x0, y0, x1, y1, linea in palabras_px:
                    r = fitz.Rect(x0 * escala, y0 * escala, x1 * escala, y1 * escala) * deroto
                    r.normalize()
                    palabras.append((texto, r, linea))
                # Reemplaza el contenido (vacío) por lo reconocido
                pag.palabras = []
                pag.texto = ""
                pag.cargar_palabras(palabras)
                pag.por_ocr = True
                procesadas += 1

        self.ocr_aplicado = self.ocr_aplicado or procesadas > 0
        return procesadas

    # ── detección de logos / membretes ─────────────────────────────────────
    def imagenes_membrete(self) -> list[dict]:
        """Imágenes incrustadas situadas en la cabecera o el pie (posibles logos).

        No aplica a páginas escaneadas (ahí toda la página es una imagen). Cada
        resultado: {pagina, rect(fitz.Rect), zona: 'cabecera'|'pie'}.
        """
        resultados = []
        with fitz.open(stream=self.contenido, filetype="pdf") as doc:
            for pag in self.paginas:
                if pag.por_ocr:
                    continue  # página escaneada: no hay imágenes «incrustadas» sueltas
                page = doc[pag.numero]
                alto = pag.alto or page.rect.height
                for img in page.get_images(full=True):
                    try:
                        rects = page.get_image_rects(img[0])
                    except Exception:
                        continue
                    for rect in rects:
                        area_rel = (rect.width * rect.height) / max(1.0, pag.ancho * alto)
                        if area_rel > 0.55:
                            continue  # imagen a página completa: no es un logo
                        centro_y = (rect.y0 + rect.y1) / 2
                        if centro_y <= alto * FRANJA_CABECERA:
                            zona = "cabecera"
                        elif centro_y >= alto * (1 - FRANJA_PIE):
                            zona = "pie"
                        else:
                            continue
                        resultados.append({"pagina": pag.numero, "rect": fitz.Rect(rect), "zona": zona})
        return resultados

    # ── conversión de offsets de texto a rectángulos ───────────────────────
    def rects_para_span(self, num_pagina: int, inicio: int, fin: int) -> list[fitz.Rect]:
        """Rectángulos que cubren las palabras del intervalo [inicio, fin).

        Las palabras de una misma línea se funden en un solo rectángulo para
        que la redacción sea continua (sin huecos entre palabras).
        """
        pag = self.paginas[num_pagina]
        por_linea: dict[tuple, fitz.Rect] = {}
        for w_ini, w_fin, rect, linea in pag.palabras:
            if w_fin <= inicio or w_ini >= fin:
                continue
            if linea in por_linea:
                por_linea[linea] |= rect  # unión de rectángulos
            else:
                por_linea[linea] = fitz.Rect(rect)
        return list(por_linea.values())

    # ── redacción destructiva ──────────────────────────────────────────────
    def redactar(
        self,
        zonas: list[tuple[int, fitz.Rect]],
        reemplazos: list[tuple[int, fitz.Rect, str]] | None = None,
    ) -> bytes:
        """Aplica redacción destructiva y devuelve el PDF resultante.

        `zonas`: lista de (número_de_página, rectángulo) que quedan en NEGRO.
        `reemplazos`: lista de (página, rectángulo, texto_nuevo) — el contenido
        original se ELIMINA igual de destructivamente, pero en su lugar se
        escribe un texto de sustitución (fechas desplazadas, rangos etarios).
        Limpia además los metadatos del documento (autor, título, XMP…).
        """
        with fitz.open(stream=self.contenido, filetype="pdf") as doc:
            for num_pagina, rect in zonas:
                if 0 <= num_pagina < len(doc):
                    # Margen de 0,5 pt para cubrir bordes de glifos
                    r = fitz.Rect(rect) + (-0.5, -0.5, 0.5, 0.5)
                    doc[num_pagina].add_redact_annot(r, fill=(0, 0, 0))
            for num_pagina, rect, texto in (reemplazos or []):
                if 0 <= num_pagina < len(doc):
                    r = fitz.Rect(rect) + (-0.5, -0.5, 0.5, 0.5)
                    # El texto original se elimina; el nuevo se dibuja encima
                    doc[num_pagina].add_redact_annot(
                        r,
                        text=texto,
                        fontname="helv",
                        fontsize=min(10.0, max(6.0, r.height * 0.72)),
                        fill=(1, 1, 1),
                        text_color=(0, 0, 0),
                        cross_out=False,
                    )
            for page in doc:
                # images=…: borra también los píxeles de imagen bajo la zona
                # (imprescindible para escaneados y logos)
                page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_PIXELS)

            # Saneado integral de PyMuPDF: elimina adjuntos y ficheros
            # incrustados, JavaScript, texto oculto, miniaturas, enlaces,
            # respuestas de formularios y sus valores. Todo ello puede guardar
            # información personal aunque no se vea al abrir la página.
            doc.scrub()
            doc.set_metadata({})
            doc.del_xml_metadata()
            return doc.tobytes(garbage=4, deflate=True, clean=True)

    def contiene_texto_oculto(self, textos: list[str]) -> list[str]:
        """Comprueba si alguno de los textos sigue presente en la capa de texto.

        Para escaneados/imágenes la verificación de restos se hace re-OCRando el
        resultado (lo hace la API), no aquí, porque el texto es un dibujo.
        """
        restante = " ".join(p.texto for p in self.paginas if not p.por_ocr).lower()
        return [t for t in textos if t.strip() and t.strip().lower() in restante]


# ── fábrica: imagen suelta (JPG/PNG/TIFF) → PDF interno de una o varias páginas ──

def pdf_desde_imagen(contenido: bytes) -> bytes:
    """Envuelve una imagen en un PDF (1 punto = 1 píxel) para procesarla igual
    que un escaneado. Soporta TIFF multipágina, corrige la orientación EXIF de
    las fotos de móvil y normaliza los modos de color raros (16 bits, CMYK…)."""
    from PIL import ImageOps

    imagen = Image.open(io.BytesIO(contenido))
    doc = fitz.open()
    n_paginas = getattr(imagen, "n_frames", 1)
    for i in range(n_paginas):
        imagen.seek(i)
        marco = imagen
        # Aplica la rotación que indica el EXIF (las fotos de móvil vienen
        # «tumbadas» y sin esto el OCR apenas reconoce nada).
        try:
            marco = ImageOps.exif_transpose(marco)
        except Exception:
            marco = imagen
        # Normaliza modos que convert('RGB') estropea: I;16 (TIFF 16 bits) da
        # una página en blanco; hay que escalar a 8 bits antes.
        if marco.mode in ("I;16", "I;16B", "I;16L", "I"):
            marco = marco.point(lambda v: v * (1.0 / 256)).convert("L")
        if marco.mode != "RGB":
            marco = marco.convert("RGB")
        buf = io.BytesIO()
        marco.save(buf, format="PNG")
        page = doc.new_page(width=marco.width, height=marco.height)
        page.insert_image(fitz.Rect(0, 0, marco.width, marco.height), stream=buf.getvalue())
    salida = doc.tobytes()
    doc.close()
    return salida
