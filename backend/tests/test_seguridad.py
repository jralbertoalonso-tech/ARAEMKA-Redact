"""Regresiones de seguridad que no usan documentos ni datos reales."""

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.seguridad import crear_cookie_sesion
from fastapi import Response


cliente = TestClient(app)


def test_api_no_se_cachea_y_lleva_cabeceras_defensivas():
    respuesta = cliente.get("/api/estado")
    assert respuesta.status_code == 200
    assert respuesta.headers["cache-control"] == "no-store"
    assert respuesta.headers["pragma"] == "no-cache"
    assert respuesta.headers["x-content-type-options"] == "nosniff"
    assert respuesta.headers["referrer-policy"] == "no-referrer"
    assert respuesta.headers["x-frame-options"] == "DENY"
    assert "default-src 'self'" in respuesta.headers["content-security-policy"]


def test_cookie_de_sesion_es_httponly_y_samesite_strict():
    respuesta = Response()
    crear_cookie_sesion(respuesta)
    cookie = respuesta.headers["set-cookie"]
    assert "HttpOnly" in cookie
    assert "SameSite=strict" in cookie
    assert "Path=/" in cookie


def test_modelos_llm_no_se_interpolan_como_html():
    frontend = Path(__file__).parents[2] / "frontend" / "app.js"
    codigo = frontend.read_text(encoding="utf-8")
    assert 'modelos.map((m) => `<option value="${m}">' not in codigo
    assert "lista.replaceChildren()" in codigo
