"""Batería de pruebas del MVP.

Ejecutar desde `backend/`:
    ../.venv/bin/python -m pytest tests/ -v

Cubre:
  - validadores de dígitos de control,
  - detección por categoría sobre texto clínico sintético,
  - redacción DESTRUCTIVA de PDF (el texto no debe poder recuperarse),
  - redacción de .docx,
  - lista blanca y lista personalizada.
"""

import fitz
import pytest

from app.detection import validators
from app.detection.motor import MOTOR
from app.documentos.docx_doc import DocumentoDocx
from app.documentos.pdf_doc import DocumentoPdf


# ══════════════════════════════════════════════════════════════════════════
# Validadores
# ══════════════════════════════════════════════════════════════════════════

def test_dni():
    assert validators.validar_dni("12345678Z")
    assert validators.validar_dni("12.345.678-Z")
    assert not validators.validar_dni("12345678A")   # letra incorrecta
    assert not validators.validar_dni("1234567Z")    # faltan dígitos


def test_nie():
    assert validators.validar_nie("X1234567L")
    assert not validators.validar_nie("X1234567A")


def test_nuss():
    assert validators.validar_nuss("388765432151")
    assert validators.validar_nuss("38 87654321 51")
    assert not validators.validar_nuss("388765432152")


def test_telefono():
    assert validators.es_telefono_es("+34 612 34 56 78")
    assert validators.es_telefono_es("922600000")
    assert not validators.es_telefono_es("123456789")   # prefijo no español
    assert not validators.es_telefono_es("6123456")     # corto


def test_codigo_postal():
    assert validators.es_codigo_postal_es("38001")
    assert validators.es_codigo_postal_es("35500")
    assert not validators.es_codigo_postal_es("99000")


# ══════════════════════════════════════════════════════════════════════════
# Motor de detección
# ══════════════════════════════════════════════════════════════════════════

TEXTO_CLINICO = """INFORME. Hospital Universitario de Pruebas. Servicio de Digestivo.
Paciente: Pedro Armas González. DNI: 12345678Z. NHC: 555123.
F. Nac.: 01/06/1980. Tel: 628 11 22 33. Correo: parmas@mail.com
Domicilio: C/ Herradores 45, 38201 La Laguna.
Ingreso el 12/01/2024. NUSS: 388765432151. CIP: BBBBBBBBAB123456
Fdo.: Dr. Luis Morera Díaz. Nº Col.: 38/38/09876"""


@pytest.fixture(scope="module")
def detecciones():
    return MOTOR.detectar(TEXTO_CLINICO)


def _de(detecciones, categoria):
    return [d["texto"] for d in detecciones if d["categoria"] == categoria]


def test_detecta_todas_las_categorias(detecciones):
    assert "Pedro Armas González" in " ".join(_de(detecciones, "persona"))
    assert _de(detecciones, "dni_nie") == ["12345678Z"]
    assert _de(detecciones, "nhc") == ["555123"]
    assert "01/06/1980" in _de(detecciones, "fecha_nacimiento")
    assert "628 11 22 33" in _de(detecciones, "telefono")
    assert _de(detecciones, "email") == ["parmas@mail.com"]
    assert any("Herradores" in t for t in _de(detecciones, "direccion"))
    assert _de(detecciones, "nuss") == ["388765432151"]
    assert _de(detecciones, "cip") == ["BBBBBBBBAB123456"]
    assert any("Luis Morera Díaz" in t for t in _de(detecciones, "sanitario"))
    assert _de(detecciones, "colegiado") == ["38/38/09876"]
    assert any("Hospital Universitario de Pruebas" in t for t in _de(detecciones, "centro"))
    assert any("Servicio de Digestivo" in t for t in _de(detecciones, "servicio_unidad"))
    assert "12/01/2024" in _de(detecciones, "fecha")


def test_interruptores_por_categoria():
    """Con solo dni_nie activo, no debe salir nada más."""
    dets = MOTOR.detectar(TEXTO_CLINICO, categorias=["dni_nie"])
    assert {d["categoria"] for d in dets} == {"dni_nie"}


def test_lista_blanca():
    dets = MOTOR.detectar(
        TEXTO_CLINICO,
        categorias=["persona"],
        lista_blanca=["Pedro Armas González"],
    )
    assert "Pedro Armas González" not in [d["texto"] for d in dets]


def test_lista_blanca_recorta_bordes():
    """Caso real: el NER pegó el nombre y la palabra de la línea siguiente en una
    sola detección. La lista blanca debe RECORTAR esa palabra del borde, no exigir
    que coincida con la detección entera."""
    from app.detection.motor import _recortar_ruido
    texto = "Gabriel Romero Santana Sertralina"
    ini, fin = _recortar_ruido(texto, 0, len(texto), extra={"sertralina"})
    assert texto[ini:fin] == "Gabriel Romero Santana"
    # y por el borde izquierdo también
    texto2 = "Sertralina Gabriel Romero Santana"
    ini2, fin2 = _recortar_ruido(texto2, 0, len(texto2), extra={"sertralina"})
    assert texto2[ini2:fin2] == "Gabriel Romero Santana"


def test_lista_personalizada():
    dets = MOTOR.detectar(
        "El paciente ingresó en el pabellón Azul-7 del centro.",
        categorias=["personalizada"],
        lista_personalizada=["Azul-7"],
    )
    assert [d["texto"] for d in dets] == ["Azul-7"]
    assert dets[0]["categoria"] == "personalizada"


def test_dni_invalido_no_se_detecta():
    """Un número con letra de control incorrecta no debe marcarse como DNI."""
    dets = MOTOR.detectar("Código interno 12345678A del expediente.", categorias=["dni_nie"])
    assert dets == []


def test_tis_con_puntos():
    """La etiqueta «T.I.S:» (variante con puntos de algunos hospitales) → cip."""
    for etiqueta in ("T.I.S:", "T.I.S.:", "TIS:", "T.I.S. nº"):
        dets = MOTOR.detectar(f"Datos del paciente. {etiqueta} 9876543210", categorias=["cip"])
        assert [d["texto"] for d in dets] == ["9876543210"], f"falla con {etiqueta!r}"
    # y no debe confundirse con palabras que empiezan por TIS
    dets = MOTOR.detectar("Biopsia de tejido TISULAR 123456789 en estudio.", categorias=["cip"])
    assert dets == []


def test_terminos_anatomicos_no_son_personas():
    """«Esófago» a inicio de línea (endoscopias) no debe marcarse como entidad."""
    texto = ("Fdo.: Dr. Luis Morera Díaz.\n"
             "Esófago: mucosa de aspecto normal.\n"
             "Estómago: sin lesiones. Duodeno: normal.")
    dets = MOTOR.detectar(texto, categorias=["persona", "sanitario", "localidad", "centro"])
    textos = " | ".join(d["texto"] for d in dets)
    assert "Esófago" not in textos
    assert "Estómago" not in textos
    assert "Duodeno" not in textos
    # el nombre del médico sí debe seguir detectándose
    assert any("Luis Morera Díaz" in d["texto"] for d in dets)


# ══════════════════════════════════════════════════════════════════════════
# Redacción destructiva de PDF
# ══════════════════════════════════════════════════════════════════════════

def _pdf_sintetico(texto: str) -> bytes:
    doc = fitz.open()
    pagina = doc.new_page()
    pagina.insert_textbox(fitz.Rect(50, 50, 545, 792), texto, fontsize=11)
    contenido = doc.tobytes()
    doc.close()
    return contenido


def test_redaccion_pdf_es_destructiva():
    secreto = "Margarita Sosa Perdomo"
    pdf = DocumentoPdf(_pdf_sintetico(f"Paciente: {secreto}. DNI: 12345678Z."))

    # Localiza el nombre y redáctalo
    pagina = pdf.paginas[0]
    inicio = pagina.texto.index(secreto)
    rects = pdf.rects_para_span(0, inicio, inicio + len(secreto))
    assert rects, "el nombre debe tener rectángulos asociados"

    resultado = pdf.redactar([(0, r) for r in rects])

    # El texto NO debe existir en el archivo final: ni extraíble ni en el binario
    final = DocumentoPdf(resultado)
    assert secreto not in " ".join(p.texto for p in final.paginas)
    assert final.contiene_texto_oculto([secreto]) == []
    assert secreto.encode() not in resultado
    # Y lo no redactado debe seguir presente
    assert "12345678Z" in final.paginas[0].texto


def test_redaccion_pdf_limpia_metadatos():
    doc = fitz.open()
    doc.new_page().insert_text((72, 72), "contenido")
    doc.set_metadata({"author": "Dra. Carmen Delgado", "title": "Informe NHC 482913"})
    pdf = DocumentoPdf(doc.tobytes())
    resultado = pdf.redactar([(0, fitz.Rect(0, 0, 10, 10))])
    with fitz.open(stream=resultado, filetype="pdf") as final:
        assert not final.metadata.get("author")
        assert not final.metadata.get("title")


# ══════════════════════════════════════════════════════════════════════════
# Redacción de .docx
# ══════════════════════════════════════════════════════════════════════════

def _docx_sintetico(parrafos: list[str]) -> bytes:
    import io
    from docx import Document
    doc = Document()
    for p in parrafos:
        doc.add_paragraph(p)
    salida = io.BytesIO()
    doc.save(salida)
    return salida.getvalue()


def test_redaccion_docx():
    secreto = "Margarita Sosa Perdomo"
    contenido = _docx_sintetico([f"Paciente: {secreto}.", "Juicio: apendicitis."])
    docx = DocumentoDocx(contenido)

    bloque = next(b for b in docx.bloques if secreto in b.texto)
    inicio = bloque.texto.index(secreto)
    resultado = docx.redactar({bloque.indice: [(inicio, inicio + len(secreto))]})

    final = DocumentoDocx(resultado)
    texto_final = "\n".join(b.texto for b in final.bloques)
    assert secreto not in texto_final
    assert "█" in texto_final
    assert "apendicitis" in texto_final       # lo demás se conserva
    assert secreto.encode() not in resultado  # tampoco en el XML crudo
