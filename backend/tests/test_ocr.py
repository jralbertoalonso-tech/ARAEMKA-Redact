"""Pruebas de la Fase 2: OCR de escaneados/imágenes y redacción destructiva de píxeles.

Se saltan automáticamente si Tesseract no está instalado en el equipo.

Ejecutar desde `backend/`:
    ../.venv/bin/python -m pytest tests/test_ocr.py -v
"""

import fitz
import pytest

from app.detection.motor import MOTOR
from app.documentos import ocr
from app.documentos.pdf_doc import DocumentoPdf, pdf_desde_imagen

# Salta todo el módulo si no hay OCR disponible
pytestmark = pytest.mark.skipif(
    not ocr.diagnostico()["disponible"],
    reason="Tesseract no está instalado en este equipo",
)

TEXTO = (
    "INFORME. Hospital Universitario de Canarias.\n"
    "Paciente: Pedro Armas Gonzalez. DNI: 12345678Z. NHC: 555123.\n"
    "Telefono: 628 11 22 33. Ingreso el 12/01/2024.\n"
    "Fdo.: Dra. Luisa Morera Diaz."
)


def _pdf_escaneado(texto: str, dpi: int = 220) -> bytes:
    """Genera un PDF SIN capa de texto (texto rasterizado a imagen)."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_textbox(fitz.Rect(40, 40, 555, 800), texto, fontsize=13)
    pix = page.get_pixmap(dpi=dpi)
    salida = fitz.open()
    p = salida.new_page(width=page.rect.width, height=page.rect.height)
    p.insert_image(p.rect, pixmap=pix)
    bytes_ = salida.tobytes()
    doc.close(); salida.close()
    return bytes_


def _png(texto: str, dpi: int = 220) -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_textbox(fitz.Rect(40, 40, 555, 800), texto, fontsize=13)
    png = page.get_pixmap(dpi=dpi).tobytes("png")
    doc.close()
    return png


def test_ocr_espanol_disponible():
    assert ocr.diagnostico()["tiene_espanol"], "falta el modelo 'spa' de Tesseract"


def test_pdf_escaneado_sin_capa_de_texto():
    doc = DocumentoPdf(_pdf_escaneado(TEXTO))
    assert not doc.tiene_texto            # es un escaneado
    assert doc.paginas_sin_texto() == [0]


def test_ocr_reconoce_y_detecta():
    doc = DocumentoPdf(_pdf_escaneado(TEXTO))
    n = doc.aplicar_ocr()
    assert n == 1
    assert doc.paginas[0].por_ocr
    texto = doc.paginas[0].texto

    dets = MOTOR.detectar(texto)
    cats = {d["categoria"] for d in dets}
    # Los identificadores clave deben salir del texto reconocido
    assert "dni_nie" in cats
    assert "persona" in cats
    assert any(d["categoria"] == "dni_nie" and "12345678Z" in d["texto"] for d in dets)


def test_redaccion_destructiva_en_escaneado():
    """Redactar sobre imagen debe borrar los píxeles: el dato no reaparece al re-OCR."""
    doc = DocumentoPdf(_pdf_escaneado(TEXTO))
    doc.aplicar_ocr()
    texto = doc.paginas[0].texto

    # Redacta el DNI y el nombre
    zonas = []
    for d in MOTOR.detectar(texto):
        if d["categoria"] in ("dni_nie", "persona"):
            for r in doc.rects_para_span(0, d["inicio"], d["fin"]):
                zonas.append((0, r))
    assert zonas
    resultado = doc.redactar(zonas)

    # Re-OCR del resultado: el DNI ya no debe leerse
    final = DocumentoPdf(resultado)
    final.aplicar_ocr()
    texto_final = final.paginas[0].texto
    assert "12345678Z" not in texto_final
    assert "Armas" not in texto_final


def test_imagen_suelta_se_convierte_y_ocr():
    doc = DocumentoPdf(pdf_desde_imagen(_png(TEXTO)))
    assert len(doc.paginas) == 1
    doc.aplicar_ocr()
    assert "12345678Z" in doc.paginas[0].texto


def test_deteccion_de_membrete():
    """Una imagen en la cabecera se detecta como posible logo."""
    doc = fitz.open()
    page = doc.new_page()
    # Imagen pequeña (logo) arriba a la izquierda
    logo = fitz.open()
    lp = logo.new_page(width=80, height=40)
    lp.draw_rect(lp.rect, fill=(0.2, 0.4, 0.8))
    pix = lp.get_pixmap()
    page.insert_image(fitz.Rect(40, 20, 160, 80), pixmap=pix)
    page.insert_text((40, 700), "Texto normal del cuerpo del documento para que tenga capa de texto.")
    contenido = doc.tobytes()
    doc.close(); logo.close()

    d = DocumentoPdf(contenido)
    membretes = d.imagenes_membrete()
    assert any(m["zona"] == "cabecera" for m in membretes)
