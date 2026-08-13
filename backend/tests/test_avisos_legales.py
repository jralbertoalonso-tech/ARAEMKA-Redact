"""Evita regresiones en las advertencias de revisión y responsabilidad."""

from pathlib import Path


RAIZ = Path(__file__).resolve().parents[2]


def _leer(ruta: str) -> str:
    return (RAIZ / ruta).read_text(encoding="utf-8")


def test_resultado_no_afirma_anonimizacion_infalible():
    html = _leer("frontend/index.html")
    idiomas = _leer("frontend/idiomas.js")

    assert "✅ Documento anonimizado" not in html
    assert '"res.titulo": "✅ Documento anonimizado"' not in idiomas
    assert 'data-i18n="res.titulo">✅ Procesamiento completado' in html
    assert idiomas.count('"res.advertencia_sin_residuos"') == 2
    assert idiomas.count('"res.advertencia_con_residuos"') == 2


def test_aviso_legal_es_visible_y_bilingue():
    html = _leer("frontend/index.html")
    idiomas = _leer("frontend/idiomas.js")

    assert 'id="boton-aviso-legal"' in html
    assert 'id="dialogo-aviso-legal"' in html
    for clave in (
        "legal.apoyo",
        "legal.limites",
        "legal.revision",
        "legal.responsabilidad",
        "legal.no_asesora",
    ):
        assert idiomas.count(f'"{clave}"') == 2


def test_condiciones_no_intentan_excluir_responsabilidad_imperativa():
    aviso = " ".join(_leer("AVISO-LEGAL.md").split())

    assert "ni garantiza la detección o eliminación completa" in aviso
    assert "responsable del tratamiento" in aviso
    assert "En la máxima medida permitida" in aviso
    assert "no permita excluir o limitar" in aviso
    assert "revisión de un profesional jurídico cualificado" in aviso


def test_ambos_portables_incluyen_el_aviso_completo():
    windows = _leer("herramientas/construir_portable_windows.bat")
    mac = _leer("herramientas/construir_portable_mac.sh")
    leeme_windows = _leer("herramientas/LEEME-WINDOWS.txt")

    assert 'AVISO-LEGAL.md" "dist\\AnoniPRO\\AVISO LEGAL.txt' in windows
    assert 'AVISO-LEGAL.md" "dist/AnoniPRO/AVISO LEGAL.txt' in mac
    assert "No garantiza la detección o eliminación" in leeme_windows
    assert "No se excluyen las responsabilidades" in leeme_windows


def test_documentacion_no_promete_que_no_quede_nada():
    readme = _leer("README.md")

    assert "para comprobar que no queda nada" not in readme
    assert "no certifica que no quede ningún dato" in readme
    assert "[AVISO-LEGAL.md](AVISO-LEGAL.md)" in readme
