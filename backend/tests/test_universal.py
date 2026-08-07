"""Pruebas de la versión universal: identificadores no sanitarios.

Cubre los datos sensibles de los perfiles jurídico, empresa, facturación y
particular: IBAN, tarjetas, CIF, matrículas, catastro, expedientes y pasaporte.

Ejecutar desde `backend/`:
    ../.venv/bin/python -m pytest tests/test_universal.py -v
"""

import pytest

from app.detection import categorias as cat
from app.detection import validators as v
from app.detection.motor import MOTOR


# ══════════════════════════════════════════════════════════════════════
# Validadores (dígitos de control reales)
# ══════════════════════════════════════════════════════════════════════

def test_iban():
    assert v.validar_iban("ES91 2100 0418 4502 0005 1332")
    assert v.validar_iban("ES9121000418450200051332")
    assert not v.validar_iban("ES9121000418450200051333")   # control incorrecto


def test_cif():
    assert v.validar_cif("A58818501")
    assert v.validar_cif("B12345674")
    assert v.validar_cif("Q2826000H")      # letra de control (organismo público)
    assert not v.validar_cif("A58818502")  # control incorrecto
    assert not v.validar_cif("12345678Z")  # eso es un DNI, no un CIF


def test_tarjeta_luhn():
    assert v.validar_tarjeta("4539 5787 6362 1486")
    assert not v.validar_tarjeta("4539 5787 6362 1487")


def test_matricula():
    assert v.es_matricula_es("1234 BCD")
    assert v.es_matricula_es("M-1234-AB")
    assert not v.es_matricula_es("1234 AEI")   # las vocales no se usan
    assert not v.es_matricula_es("123 BCD")


def test_referencia_catastral():
    assert v.validar_referencia_catastral("9872023VH5797S0001WX")
    assert not v.validar_referencia_catastral("98720231234567890123")  # sin letras
    assert not v.validar_referencia_catastral("9872023VH5797S0001")    # corta


# ══════════════════════════════════════════════════════════════════════
# Detección en documentos reales de cada perfil
# ══════════════════════════════════════════════════════════════════════

CONTRATO = (
    "Ante mi, Dna. Marta Ruiz Sanz, Notaria de Santa Cruz de Tenerife, protocolo n 1245/2024. "
    "Comparece D. Antonio Medina Cabrera, con DNI 12345678Z y pasaporte n XDA123456. "
    "En representacion de TALLERES PEREZ, S.L., con CIF A58818501. "
    "Pago mediante ES91 2100 0418 4502 0005 1332 y tarjeta 4539 5787 6362 1486. "
    "Vehiculo: matricula 1234 BCD. Inmueble con referencia catastral 9872023VH5797S0001WX. "
    "Juzgado de Primera Instancia n 3, autos 512/2024."
)


@pytest.fixture(scope="module")
def det_contrato():
    return {d["categoria"]: [x["texto"] for x in MOTOR.detectar(CONTRATO)
                             if x["categoria"] == d["categoria"]]
            for d in MOTOR.detectar(CONTRATO)}


def test_contrato_detecta_datos_juridicos(det_contrato):
    assert "ES91 2100 0418 4502 0005 1332" in det_contrato.get("iban", [])
    assert "4539 5787 6362 1486" in det_contrato.get("tarjeta", [])
    assert "A58818501" in det_contrato.get("cif", [])
    assert "1234 BCD" in det_contrato.get("matricula", [])
    assert "9872023VH5797S0001WX" in det_contrato.get("catastro", [])
    assert "XDA123456" in det_contrato.get("pasaporte", [])
    assert "12345678Z" in det_contrato.get("dni_nie", [])
    # Expedientes: protocolo notarial y autos judiciales
    exp = det_contrato.get("expediente", [])
    assert any("1245/2024" in e for e in exp) and any("512/2024" in e for e in exp)
    # Organizaciones: la sociedad y el juzgado
    org = " | ".join(det_contrato.get("organizacion", []))
    assert "TALLERES PEREZ" in org and "Juzgado" in org


def test_iban_no_se_come_la_palabra_siguiente():
    """Regresión: con IGNORECASE el patrón absorbía la palabra de al lado y la
    validación descartaba el IBAN entero."""
    dets = MOTOR.detectar("Abono en cuenta ES91 2100 0418 4502 0005 1332 Total devengado",
                          categorias=["iban"])
    assert [d["texto"] for d in dets] == ["ES91 2100 0418 4502 0005 1332"]


def test_factura_y_nomina():
    factura = ("FACTURA F-2024-0451 de GESTORIA MARTIN Y ASOCIADOS, S.L. CIF B12345674. "
               "Cliente: Nieves Toledo Garcia, ntoledo@ejemplo.es, 922 24 55 66.")
    cats = {d["categoria"] for d in MOTOR.detectar(factura)}
    assert {"cif", "email", "telefono", "persona", "expediente"} <= cats

    nomina = ("Trabajador: Yeray Santana Marrero DNI 43811223H. "
              "NAF Seguridad Social: 38 44556677 89. Abono en ES9121000418450200051332.")
    cats2 = {d["categoria"] for d in MOTOR.detectar(nomina)}
    assert {"persona", "dni_nie", "nuss", "iban"} <= cats2


def test_no_confunde_numeros_normales_con_tarjetas():
    """Un número largo cualquiera que no pase Luhn no debe marcarse."""
    dets = MOTOR.detectar("El importe total asciende a 1234 5678 9012 3456 euros.",
                          categorias=["tarjeta"])
    assert dets == []


# ══════════════════════════════════════════════════════════════════════
# Catálogo y perfiles
# ══════════════════════════════════════════════════════════════════════

def test_catalogo_expone_grupos_ordenados():
    datos = cat.como_dict()
    ids = {c["id"] for c in datos}
    # Las categorías nuevas de uso general están presentes
    assert {"iban", "tarjeta", "cif", "matricula", "catastro", "expediente",
            "pasaporte", "organizacion"} <= ids
    # Cada categoría trae el nombre y el orden de su grupo (los pinta el frontend)
    for c in datos:
        assert c["grupo_nombre"] and isinstance(c["orden_grupo"], int)
    # Y las de salud siguen ahí
    assert {"cip", "nhc", "nuss", "sanitario", "centro"} <= ids
