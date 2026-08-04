"""OCR local con Tesseract (motor de la Fase 2).

Se usa Tesseract con el modelo español (`spa`). Justificación frente a otras
opciones (EasyOCR, PaddleOCR, docTR): Tesseract es maduro, ligero, funciona
100 % en CPU y sin conexión, se instala fácil en el contenedor del NAS
(`apt-get install tesseract-ocr-spa`) y —lo más importante para nosotros—
devuelve la **caja delimitadora de cada palabra**, que es justo lo que
necesitamos para redactar de forma destructiva sobre la imagen. Los motores
basados en deep learning dan algo más de precisión pero pesan cientos de MB,
descargan modelos y rinden mal sin GPU (el NAS DS923+ no tiene). Si en el
futuro se quiere más precisión, este módulo aísla el OCR para poder cambiarlo.

Todo el reconocimiento ocurre en local; Tesseract no hace ninguna llamada de red.
"""

import functools
import io

import pytesseract
from PIL import Image

# Confianza mínima (0-100) para quedarnos con una palabra reconocida.
# Por debajo suele ser ruido (bordes, manchas del escaneo).
CONFIANZA_MINIMA_OCR = 40


class OcrNoDisponible(RuntimeError):
    """Se lanza cuando Tesseract no está instalado en el sistema."""


@functools.lru_cache(maxsize=1)
def diagnostico() -> dict:
    """Comprueba una sola vez si Tesseract y el modelo español están disponibles."""
    try:
        version = str(pytesseract.get_tesseract_version())
        idiomas = pytesseract.get_languages(config="")
    except Exception:
        return {"disponible": False, "version": None, "tiene_espanol": False, "idiomas": []}
    return {
        "disponible": True,
        "version": version,
        "tiene_espanol": "spa" in idiomas,
        "idiomas": idiomas,
    }


def _idioma() -> str:
    """Usa español si está; si no, cae a inglés con aviso implícito en el log."""
    diag = diagnostico()
    if not diag["disponible"]:
        raise OcrNoDisponible(
            "Tesseract no está instalado. En macOS: «brew install tesseract tesseract-lang». "
            "En el NAS ya viene incluido en la imagen Docker."
        )
    if diag["tiene_espanol"]:
        return "spa"
    return "eng"


def palabras_de_imagen(imagen: Image.Image) -> list[tuple[str, float, float, float, float, int]]:
    """Ejecuta OCR sobre una imagen PIL y devuelve las palabras con su posición.

    Devuelve una lista de tuplas:
        (texto, x0, y0, x1, y1, nº_de_línea)
    con las coordenadas en PÍXELES de la imagen. El nº de línea agrupa palabras
    de la misma línea (bloque·párrafo·línea de Tesseract) para fusionarlas luego.
    """
    if imagen.mode not in ("RGB", "L"):
        imagen = imagen.convert("RGB")

    datos = pytesseract.image_to_data(
        imagen, lang=_idioma(), output_type=pytesseract.Output.DICT
    )

    palabras = []
    n = len(datos["text"])
    for i in range(n):
        texto = datos["text"][i].strip()
        if not texto:
            continue
        try:
            conf = float(datos["conf"][i])
        except (ValueError, TypeError):
            conf = -1
        if conf < CONFIANZA_MINIMA_OCR:
            continue
        x, y, w, h = datos["left"][i], datos["top"][i], datos["width"][i], datos["height"][i]
        # Clave de línea estable: página·bloque·párrafo·línea
        clave_linea = (
            datos["block_num"][i],
            datos["par_num"][i],
            datos["line_num"][i],
        )
        palabras.append((texto, float(x), float(y), float(x + w), float(y + h), clave_linea))

    return palabras


def imagen_desde_bytes(contenido: bytes) -> Image.Image:
    """Abre una imagen desde bytes (JPG, PNG, TIFF de una sola página)."""
    return Image.open(io.BytesIO(contenido))
