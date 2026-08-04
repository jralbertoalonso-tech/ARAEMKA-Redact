"""Pruebas de la Fase 3: diagnóstico de hardware y capa 3 (LLM local).

No requieren ningún LLM en marcha: se prueba el diagnóstico, el parseo de la
respuesta del modelo, la localización literal de fragmentos y el camino de
«endpoint no disponible» (que nunca debe romper el flujo).

Ejecutar desde `backend/`:
    ../.venv/bin/python -m pytest tests/test_capa3.py -v
"""

from app.detection import capa3_llm as capa3
from app.detection import diagnostico_hardware as dh


# ── diagnóstico de hardware ────────────────────────────────────────────────

def test_detectar_devuelve_campos():
    hw = dh.detectar()
    assert hw["sistema"] in ("macOS", "Windows", "Linux")
    assert "aceleracion" in hw


def test_recomendacion_mac_con_ram_alta():
    hw = {"sistema": "macOS", "es_apple_silicon": True, "aceleracion": "Apple Silicon (Metal)",
          "ram_total_gb": 32.0, "ram_disponible_gb": 20.0}
    rec = dh.recomendar(hw)
    assert rec["puede_local"] is True
    assert rec["modelo"] == "qwen3:8b"
    assert any("ollama pull" in c for paso in rec["pasos"] for c in paso["comandos"])


def test_recomendacion_equipo_justo():
    hw = {"sistema": "Windows", "es_apple_silicon": False, "aceleracion": "Solo CPU",
          "ram_total_gb": 8.0, "ram_disponible_gb": 5.0}
    rec = dh.recomendar(hw)
    assert rec["puede_local"] is True
    # 8 GB → modelo pequeño (qwen3:4b según el catálogo)
    assert rec["modelo"] in ("qwen3:4b", "gemma3:4b", "llama3.2:3b")


def test_recomendacion_nas_delega():
    hw = {"sistema": "Linux", "es_apple_silicon": False, "aceleracion": "Solo CPU",
          "ram_total_gb": 32.0, "ram_disponible_gb": 28.0}
    rec = dh.recomendar(hw)
    assert rec["puede_local"] is False       # el NAS NO corre el LLM
    assert "otro equipo" in rec["resumen"].lower() or "delega" in rec["resumen"].lower()


# ── capa 3: parseo y localización ──────────────────────────────────────────

def test_extraer_json_tolera_vallas_y_texto():
    assert capa3._extraer_json('```json\n{"entidades":[]}\n```') == {"entidades": []}
    assert capa3._extraer_json('Claro:\n{"entidades":[{"texto":"X","tipo":"persona"}]}') \
        == {"entidades": [{"texto": "X", "tipo": "persona"}]}
    assert capa3._extraer_json("no es json") == {}


def test_capa3_desactivada_devuelve_vacio():
    capa3.CONFIG.actualizar(activa=False)
    assert capa3.revisar_texto("Paciente Juan Pérez.", {"persona"}) == []


def test_capa3_endpoint_caido_no_rompe():
    # Activada pero apuntando a un puerto sin servidor → [] sin excepción
    capa3.CONFIG.actualizar(activa=True, endpoint="http://127.0.0.1:59999", modelo="x")
    assert capa3.revisar_texto("Paciente Juan Pérez.", {"persona"}) == []
    capa3.CONFIG.actualizar(activa=False)


def test_localizacion_de_fragmentos(monkeypatch):
    """Simula la respuesta del LLM y comprueba que localiza el fragmento literal."""
    texto = "El paciente Anselmo Quesada Brito acudió acompañado de su vecino Tomás."

    def fake_post(url, cuerpo, timeout):
        return {"choices": [{"message": {"content":
            '{"entidades":[{"texto":"Anselmo Quesada Brito","tipo":"persona"},'
            '{"texto":"Tomás","tipo":"persona"},'
            '{"texto":"NO EXISTE EN EL TEXTO","tipo":"persona"}]}'}}]}

    monkeypatch.setattr(capa3, "_post_json", fake_post)
    capa3.CONFIG.actualizar(activa=True, endpoint="http://x:1", modelo="m")
    dets = capa3.revisar_texto(texto, {"persona"})
    capa3.CONFIG.actualizar(activa=False)

    textos = {d["texto"] for d in dets}
    assert "Anselmo Quesada Brito" in textos
    assert "Tomás" in textos
    # Lo que el modelo «inventa» y no aparece literalmente se descarta
    assert "NO EXISTE EN EL TEXTO" not in textos
    # Todas marcadas como capa 3 y con offsets correctos
    for d in dets:
        assert d["capa"] == 3
        assert texto[d["inicio"]:d["fin"]] == d["texto"]


def test_capa3_respeta_categorias_activas(monkeypatch):
    texto = "Llamar al 928123456 o escribir a ana@correo.es."

    def fake_post(url, cuerpo, timeout):
        return {"choices": [{"message": {"content":
            '{"entidades":[{"texto":"928123456","tipo":"telefono"},'
            '{"texto":"ana@correo.es","tipo":"email"}]}'}}]}

    monkeypatch.setattr(capa3, "_post_json", fake_post)
    capa3.CONFIG.actualizar(activa=True, endpoint="http://x:1", modelo="m")
    # Solo 'email' activo → el teléfono no debe colarse
    dets = capa3.revisar_texto(texto, {"email"})
    capa3.CONFIG.actualizar(activa=False)
    assert {d["categoria"] for d in dets} == {"email"}
