"""Pruebas de la Fase 5: desplazamiento consistente de fechas y rangos etarios.

Ejecutar desde `backend/`:
    ../.venv/bin/python -m pytest tests/test_fase5.py -v
"""

import io
import re
from datetime import date

import fitz
from fastapi.testclient import TestClient

from app.documentos import fechas
from app.main import app

cliente = TestClient(app)


# ── unidad: desplazar_fecha ────────────────────────────────────────────────

def test_desplaza_conservando_formato():
    assert fechas.desplazar_fecha("12/03/2015", 10) == "22/03/2015"
    assert fechas.desplazar_fecha("28-02-2024", 2) == "01-03-2024"   # bisiesto
    assert fechas.desplazar_fecha("01.01.24", -5) == "27.12.23"      # año corto
    assert fechas.desplazar_fecha("2024-04-18", 30) == "2024-05-18"  # ISO
    assert fechas.desplazar_fecha("3 de mayo de 2024", 40) == "12 de junio de 2024"
    assert fechas.desplazar_fecha("mayo de 2024", 60) == "julio de 2024"


def test_fecha_no_interpretable_devuelve_none():
    assert fechas.desplazar_fecha("99/99/2024", 10) is None   # fecha imposible
    assert fechas.desplazar_fecha("ayer por la tarde", 10) is None


def test_mismo_delta_conserva_intervalos():
    d1 = fechas.desplazar_fecha("12/04/2024", 117)
    d2 = fechas.desplazar_fecha("18/04/2024", 117)
    f1 = date(*reversed([int(x) for x in d1.split("/")]))
    f2 = date(*reversed([int(x) for x in d2.split("/")]))
    assert (f2 - f1).days == 6   # el intervalo original se mantiene


# ── unidad: rango etario ───────────────────────────────────────────────────

def test_rango_etario():
    assert fechas.rango_etario("47 años") == "45-49 años"
    assert fechas.rango_etario("8 años de edad") == "5-9 años de edad"
    assert fechas.rango_etario("92 años") == "85 o más años"
    assert fechas.rango_etario("7 meses de edad") == "menor de 1 año de edad"
    assert fechas.rango_etario("12/03/2015") is None   # una fecha no es una edad
    assert fechas.es_edad("47 años") and not fechas.es_edad("12/03/2015")


# ── extremo a extremo por la API ───────────────────────────────────────────

TEXTO = (
    "Paciente de 47 años. F. Nac.: 12/03/1977. DNI: 12345678Z. "
    "Fecha de ingreso: 12/04/2024. Fecha de alta: 18/04/2024."
)


def _pdf(texto: str) -> bytes:
    doc = fitz.open()
    doc.new_page().insert_textbox(fitz.Rect(50, 50, 545, 780), texto, fontsize=11)
    contenido = doc.tobytes()
    doc.close()
    return contenido


def test_flujo_desplazar_y_rango():
    r = cliente.post(
        "/api/documentos",
        files={"archivo": ("f5.pdf", io.BytesIO(_pdf(TEXTO)), "application/pdf")},
        data={"categorias": "[]", "lista_personalizada": "[]", "lista_blanca": "[]"},
    )
    doc = r.json()
    ids = [d["id"] for d in doc["detecciones"]]

    r2 = cliente.post(f"/api/documentos/{doc['id']}/redactar", json={
        "aprobadas": ids, "zonas_manuales": [], "textos_manuales": [],
        "opciones": {"fechas": "desplazar", "edad": "rango"},
    })
    assert r2.status_code == 200
    datos = r2.json()
    # Las fechas desplazadas y el rango no deben aparecer como residuales
    assert not any(x["categoria"] in ("fecha", "fecha_nacimiento")
                   for x in datos["residuales"])

    # Descargar y extraer el texto final
    pdf = cliente.get(datos["url_descarga"]).content
    with fitz.open(stream=pdf, filetype="pdf") as f:
        texto_final = " ".join(p.get_text() for p in f)

    # Originales fuera
    assert "12/04/2024" not in texto_final
    assert "18/04/2024" not in texto_final
    assert "12/03/1977" not in texto_final      # la F. de nacimiento se tacha siempre
    assert "47 años" not in texto_final
    assert "12345678Z" not in texto_final
    # El rango etario está
    assert "45-49 años" in texto_final
    # Hay dos fechas nuevas y conservan el intervalo de 6 días
    nuevas = re.findall(r"\b(\d{2})/(\d{2})/(\d{4})\b", texto_final)
    assert len(nuevas) == 2, f"esperaba 2 fechas desplazadas, hay {len(nuevas)}"
    f1, f2 = [date(int(a), int(m), int(d)) for d, m, a in nuevas]
    assert abs((f2 - f1).days) == 6
    # Y no son las originales
    assert {str(f1), str(f2)} != {"2024-04-12", "2024-04-18"}

    # La auditoría registra el MODO pero no el desplazamiento
    aud = cliente.get(datos["url_auditoria"]).json()
    assert aud["redaccion"]["modo_fechas"] == "desplazadas"
    assert aud["redaccion"]["modo_edad"] == "rango_etario"
    import json as _json
    assert "delta" not in _json.dumps(aud).lower()


def test_flujo_por_defecto_sigue_redactando():
    """Sin opciones, las fechas se tachan como siempre (compatibilidad)."""
    r = cliente.post(
        "/api/documentos",
        files={"archivo": ("f5b.pdf", io.BytesIO(_pdf(TEXTO)), "application/pdf")},
        data={"categorias": "[]", "lista_personalizada": "[]", "lista_blanca": "[]"},
    )
    doc = r.json()
    r2 = cliente.post(f"/api/documentos/{doc['id']}/redactar", json={
        "aprobadas": [d["id"] for d in doc["detecciones"]],
        "zonas_manuales": [], "textos_manuales": [],
    })
    pdf = cliente.get(r2.json()["url_descarga"]).content
    with fitz.open(stream=pdf, filetype="pdf") as f:
        texto_final = " ".join(p.get_text() for p in f)
    assert not re.search(r"\d{2}/\d{2}/\d{4}", texto_final)  # ninguna fecha visible
