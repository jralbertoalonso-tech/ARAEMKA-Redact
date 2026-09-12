"""Evita regresiones en las advertencias de revisión y responsabilidad."""

import re
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
        "legal.licencia",
        "legal.codigo_fuente",
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


def test_agpl_y_codigo_fuente_son_visibles_y_se_distribuyen():
    html = _leer("frontend/index.html")
    idiomas = _leer("frontend/idiomas.js")
    aviso = _leer("AVISO-LEGAL.md")
    readme = _leer("README.md")

    assert "AGPL-3.0-only" in aviso
    assert "AGPL-3.0-only" in readme
    assert "github.com/jralbertoalonso-tech/ARAEMKA-Redact" in html
    assert idiomas.count('"legal.codigo_fuente"') == 2
    for ruta in ("LICENSE", "CODIGO-FUENTE.md", "THIRD-PARTY-NOTICES.md", "TRADEMARKS.md"):
        assert (RAIZ / ruta).is_file()


def test_ambos_portables_incluyen_el_aviso_completo():
    windows = _leer("herramientas/construir_portable_windows.bat")
    mac = _leer("herramientas/construir_portable_mac.sh")
    leeme_windows = _leer("herramientas/LEEME-WINDOWS.txt")

    assert 'AVISO-LEGAL.md" "dist\\ARAEMKA-Redact\\AVISO LEGAL.txt' in windows
    assert 'AVISO-LEGAL.md" "dist/ARAEMKA-Redact/AVISO LEGAL.txt' in mac
    assert 'LICENSE" "dist\\ARAEMKA-Redact\\LICENSE.txt' in windows
    assert 'LICENSE" "dist/ARAEMKA-Redact/LICENSE.txt' in mac
    assert "generar_avisos_terceros.py" in windows
    assert "generar_avisos_terceros.py" in mac
    assert "No garantiza la detección o eliminación" in leeme_windows
    assert "No se excluyen las responsabilidades" in leeme_windows


def test_documentacion_no_promete_que_no_quede_nada():
    readme = _leer("README.md")

    assert "para comprobar que no queda nada" not in readme
    assert "no certifica que no quede ningún dato" in readme
    assert "[AVISO-LEGAL.md](AVISO-LEGAL.md)" in readme


def test_marca_publica_y_compatibilidad_tecnica():
    html = _leer("frontend/index.html")
    idiomas = _leer("frontend/idiomas.js")
    app_js = _leer("frontend/app.js")
    windows = _leer("herramientas/construir_portable_windows.bat")
    mac = _leer("herramientas/construir_portable_mac.sh")

    assert "ARAEMKA Redact" in html
    assert "ARAEMKA Redact" in idiomas
    assert "ARAEMKA-Redact.exe" in windows
    assert "ARAEMKA-Redact-portable-windows" in windows
    assert "ARAEMKA-Redact-portable-macos" in mac
    # Se conservan las claves para no perder preferencias al actualizar.
    assert 'localStorage.getItem("anonipro_idioma")' in app_js
    assert 'localStorage.getItem("anonipro_perfiles")' in app_js


def test_autoria_publica_sin_titulo_profesional_ni_afiliacion():
    rutas_publicas = (
        "README.md",
        "README.en.md",
        "AVISO-LEGAL.md",
        "frontend/index.html",
        "frontend/idiomas.js",
        "web/index.html",
        "herramientas/LEEME-WINDOWS.txt",
        "herramientas/construir_portable_mac.sh",
        "herramientas/generar_version_windows.py",
        "herramientas/ficha_tecnica.py",
    )
    contenido = "\n".join(_leer(ruta) for ruta in rutas_publicas)
    autor = "José Ramón Alberto Alonso"

    assert not re.search(rf"\bDr\.?\s+{re.escape(autor)}", contenido)
    for linea in (linea for linea in contenido.splitlines() if autor in linea):
        assert "hospital" not in linea.casefold()
        assert "servicio" not in linea.casefold()
        assert "sistema público" not in linea.casefold()


def test_ejemplos_clinicos_declaran_centros_ficticios():
    rutas_ejemplos = (
        "herramientas/generar_documentos_prueba.py",
        "herramientas/evaluar_deteccion.py",
        "backend/tests/test_mvp.py",
        "backend/tests/test_ocr.py",
        "backend/tests/test_correcciones.py",
    )
    contenido = "\n".join(_leer(ruta) for ruta in rutas_ejemplos)

    for marcador_ficticio in (
        "Hospital Universitario de Pruebas",
        "Hospital Universitario de Ejemplo",
        "Hospital General de Ejemplo",
        "Centro de Salud Alfa",
        "Clínica Beta",
        "Consultorio Gamma",
        "example.org",
    ):
        assert marcador_ficticio in contenido
