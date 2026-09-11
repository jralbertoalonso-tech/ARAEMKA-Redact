"""Pruebas del OCR autocontenido en los paquetes portables."""

import os
import sys

from app.documentos import ocr


def test_portable_prioriza_tesseract_incluido(monkeypatch, tmp_path):
    """El portable usa su OCR interno aunque el equipo tenga otro instalado."""
    interno = tmp_path / "tesseract"
    tessdata = interno / "tessdata"
    tessdata.mkdir(parents=True)
    ejecutable = interno / "tesseract.exe"
    ejecutable.write_bytes(b"")

    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    monkeypatch.setattr(ocr.pytesseract.pytesseract, "tesseract_cmd", "tesseract")
    monkeypatch.delenv("TESSDATA_PREFIX", raising=False)

    ocr._localizar_tesseract()

    assert ocr.pytesseract.pytesseract.tesseract_cmd == str(ejecutable)
    assert os.environ["TESSDATA_PREFIX"] == str(tessdata)


def test_ocr_bilingue_cuando_estan_los_dos_modelos(monkeypatch):
    monkeypatch.setattr(
        ocr,
        "diagnostico",
        lambda: {"disponible": True, "tiene_espanol": True, "tiene_ingles": True},
    )
    assert ocr._idioma() == "spa+eng"
