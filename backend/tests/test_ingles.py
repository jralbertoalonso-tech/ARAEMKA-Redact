"""Pruebas del motor de detección en INGLÉS (Reino Unido y EE. UU.).

Cubren:
  - los validadores con dígito/formato de control (NHS, NINO, SSN, ITIN…),
  - la detección automática del idioma del documento,
  - el enrutado: un documento en inglés usa el motor inglés y detecta sus
    identificadores propios, y un documento en español NO los detecta (ni al
    revés), lo que evita fugas por analizar con el idioma equivocado.

Ejecutar desde `backend/`:
    ../.venv/bin/python -m pytest tests/test_ingles.py -v
"""

from app.detection import validators as v
from app.detection.idioma import detectar_idioma
from app.detection.motor import MOTOR


# ── validadores con control ────────────────────────────────────────────────

def test_nhs_digito_control():
    assert v.validar_nhs("943 476 5919") is True     # ejemplo oficial válido
    assert v.validar_nhs("9434765919") is True       # sin separadores
    assert v.validar_nhs("943 476 5918") is False     # último dígito cambiado
    assert v.validar_nhs("123 456 7890") is False     # control no cuadra
    assert v.validar_nhs("94347659") is False         # longitud incorrecta


def test_nino_formato():
    assert v.es_nino("AB123456C") is True
    assert v.es_nino("AB 12 34 56 C") is True         # con espacios
    assert v.es_nino("DA123456A") is False            # D prohibida en 1ª posición
    assert v.es_nino("AO123456A") is False            # O prohibida en 2ª posición
    assert v.es_nino("BG123456A") is False            # prefijo administrativo no válido
    assert v.es_nino("AB123456E") is False            # sufijo fuera de A-D


def test_ssn_rangos():
    assert v.es_ssn("123-45-6789") is True
    assert v.es_ssn("000-45-6789") is False           # área 000
    assert v.es_ssn("666-45-6789") is False           # área 666
    assert v.es_ssn("900-45-6789") is False           # área ≥ 900
    assert v.es_ssn("123-00-6789") is False           # grupo 00
    assert v.es_ssn("123-45-0000") is False           # serie 0000


def test_itin_distinto_de_ssn():
    assert v.es_itin("912-70-1234") is True           # empieza por 9, grupo 70
    assert v.es_itin("912-40-1234") is False          # grupo 40 fuera de rango
    assert v.es_ssn("912-70-1234") is False           # un ITIN no es un SSN


def test_codigos_postales_y_telefonos():
    assert v.es_codigo_postal_uk("SW1A 1AA") is True
    assert v.es_codigo_postal_uk("M1 1AE") is True
    assert v.es_zip_us("90210") is True
    assert v.es_zip_us("90210-1234") is True
    assert v.es_telefono_us("(415) 555-2671") is True
    assert v.es_telefono_us("123-45-6789") is False   # no es un teléfono
    assert v.es_telefono_uk("+44 20 7946 0958") is True


# ── detección automática de idioma ─────────────────────────────────────────

def test_deteccion_idioma():
    es = "El paciente acude a Urgencias con dolor abdominal de dos días de evolución."
    en = "The patient was admitted to the emergency department with abdominal pain."
    assert detectar_idioma(es) == "es"
    assert detectar_idioma(en) == "en"
    # Ante muy poco texto o duda, español (opción conservadora)
    assert detectar_idioma("") == "es"
    assert detectar_idioma("12345 67890") == "es"


# ── motor inglés de extremo a extremo ──────────────────────────────────────

TEXTO_EN = (
    "PATIENT DISCHARGE SUMMARY. "
    "Patient: John A. Smith. DOB: 05/14/1978. "
    "NHS No: 943 476 5919. Address: 12 Oak Street, Manchester M1 1AE. "
    "Email: john.smith@example.co.uk. Phone: +44 20 7946 0958. "
    "Consultant: Dr. Emily Carter reviewed the patient on March 3, 2024. "
    "National Insurance: AB123456C. SSN: 123-45-6789."
)


def _cats(texto, idioma):
    return {d["categoria"]: d["texto"] for d in MOTOR.detectar(texto, idioma=idioma)}


def test_motor_ingles_detecta_identificadores():
    cats = _cats(TEXTO_EN, "en")
    assert "nhs" in cats and cats["nhs"].replace(" ", "") == "9434765919"
    assert "nino" in cats and cats["nino"] == "AB123456C"
    assert "ssn" in cats and cats["ssn"] == "123-45-6789"
    assert "email" in cats
    assert "telefono" in cats


def test_motor_ingles_detecta_nombres_por_contexto():
    dets = MOTOR.detectar(TEXTO_EN, idioma="en")
    textos = {d["texto"] for d in dets}
    assert any("Smith" in t for t in textos)       # paciente
    assert any("Carter" in t for t in textos)      # médico (Dr.)


def test_identificadores_ingleses_no_se_detectan_en_espanol():
    """Un NHS/NINO/SSN en un texto analizado como español NO debe salir: sus
    reconocedores solo existen en el motor inglés."""
    cats = _cats(TEXTO_EN, "es")
    assert "nhs" not in cats
    assert "nino" not in cats
    assert "ssn" not in cats


def test_identificadores_espanoles_no_se_detectan_en_ingles():
    """Simétrico: un DNI o CIP no debe detectarse en el motor inglés."""
    texto_es = "El paciente tiene DNI 12345678Z y CIP AUT: 1234567890 en su historia."
    cats = _cats(texto_es, "en")
    assert "dni_nie" not in cats
    assert "cip" not in cats
