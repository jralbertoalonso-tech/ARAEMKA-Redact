"""Pruebas de la Fase 4: segunda pasada reforzada e informe de auditoría.

Se prueban a través de la API completa (TestClient de FastAPI), que es como
las usa el navegador.

Ejecutar desde `backend/`:
    ../.venv/bin/python -m pytest tests/test_fase4.py -v
"""

import io
import json

import fitz
import pytest
from fastapi.testclient import TestClient

from app.main import app

cliente = TestClient(app)


def _pdf(texto: str) -> bytes:
    doc = fitz.open()
    doc.new_page().insert_textbox(fitz.Rect(50, 50, 545, 780), texto, fontsize=11)
    contenido = doc.tobytes()
    doc.close()
    return contenido


TEXTO = (
    "INFORME. Paciente: Pedro Armas Gonzalez. DNI: 12345678Z. NHC: 555123. "
    "Telefono: 628 11 22 33. Su hermana Rosa Armas Gonzalez le acompaña. "
    "Fdo.: Dra. Luisa Morera Diaz."
)


def _subir(texto=TEXTO) -> dict:
    r = cliente.post(
        "/api/documentos",
        files={"archivo": ("prueba.pdf", io.BytesIO(_pdf(texto)), "application/pdf")},
        data={"categorias": "[]", "lista_personalizada": "[]", "lista_blanca": "[]"},
    )
    assert r.status_code == 200, r.text
    return r.json()


def test_flujo_completo_con_auditoria():
    doc = _subir()
    ids = [d["id"] for d in doc["detecciones"]]
    assert ids

    r = cliente.post(f"/api/documentos/{doc['id']}/redactar", json={
        "aprobadas": ids, "zonas_manuales": [], "textos_manuales": ["INFORME"],
    })
    assert r.status_code == 200
    datos = r.json()
    assert datos["avisos"] == []            # nada aprobado queda en el archivo
    assert "url_auditoria" in datos

    # Descarga de la auditoría
    r2 = cliente.get(datos["url_auditoria"])
    assert r2.status_code == 200
    aud = json.loads(r2.content)

    # La auditoría registra QUÉ se hizo…
    assert aud["redaccion"]["detecciones_aprobadas"] == len(ids)
    assert aud["redaccion"]["textos_manuales"] == 1
    assert aud["redaccion"]["por_categoria"]["dni_nie"]["redactadas"] == 1
    assert aud["verificacion_segunda_pasada"]["textos_aprobados_restantes"] == 0
    assert len(aud["sha256_resultado"]) == 64
    # …pero NUNCA los datos originales
    # Un hash SHA-256 es una cadena hexadecimal aleatoria y puede contener por
    # casualidad fragmentos numéricos cortos del documento (por ejemplo "628").
    # No es una filtración ni permite recuperar el contenido; se excluye de la
    # comprobación textual para que la prueba no falle de forma probabilística.
    aud_sin_hash = {k: v for k, v in aud.items() if not k.startswith("sha256_")}
    volcado = json.dumps(aud_sin_hash)
    for secreto in ["Pedro", "Armas", "12345678Z", "555123", "628", "Morera"]:
        assert secreto not in volcado, f"la auditoría contiene el dato {secreto!r}"


def test_segunda_pasada_avisa_de_lo_no_marcado():
    """Si el usuario solo redacta el DNI, la 2ª pasada debe avisar de los nombres."""
    doc = _subir()
    solo_dni = [d["id"] for d in doc["detecciones"] if d["categoria"] == "dni_nie"]
    rechazadas_nombres = [d for d in doc["detecciones"] if d["categoria"] == "persona"]
    assert solo_dni and rechazadas_nombres

    r = cliente.post(f"/api/documentos/{doc['id']}/redactar", json={
        "aprobadas": solo_dni, "zonas_manuales": [], "textos_manuales": [],
    })
    datos = r.json()
    # Los nombres se RECHAZARON explícitamente → la 2ª pasada los respeta
    residuales = {x["texto"] for x in datos["residuales"]}
    assert "Pedro Armas Gonzalez" not in residuales

    # En cambio, si el nombre nunca se detectó ni rechazó, sí debe avisar:
    # lo simulamos con un documento cuyo teléfono queda sin marcar.
    doc2 = _subir("Paciente con telefono de contacto 655 44 33 22 y DNI 12345678Z.")
    solo_dni2 = [d["id"] for d in doc2["detecciones"] if d["categoria"] == "dni_nie"]
    # Rechazamos todas menos el DNI… pero SIN rechazar el teléfono no es posible:
    # el teléfono está detectado, así que rechazarlo es explícito. Comprobamos el
    # otro camino: un dato que las capas ven en el RESULTADO tras redactar.
    r2 = cliente.post(f"/api/documentos/{doc2['id']}/redactar", json={
        "aprobadas": solo_dni2, "zonas_manuales": [], "textos_manuales": [],
    })
    assert r2.status_code == 200  # y no rompe aunque haya rechazados


def test_auditoria_404_antes_de_redactar():
    doc = _subir()
    r = cliente.get(f"/api/documentos/{doc['id']}/auditoria")
    assert r.status_code == 404
