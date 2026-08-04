"""Capa 3 — Revisión semántica opcional con un LLM local (Ollama / LM Studio).

Esta capa es OPCIONAL. La aplicación funciona perfectamente sin ella (capas 1-2).
Si el usuario la activa, se envía el texto a un LLM que corre en LOCAL (en el
propio equipo o en otro de la red) a través de la API compatible con OpenAI
(`/v1/chat/completions`), que exponen tanto Ollama como LM Studio. Ningún dato
sale de la red local.

El LLM se usa solo para CAZAR lo que las capas 1-2 no vieron: nombres poco
frecuentes, menciones indirectas del paciente, etc. Se le exige devolver los
fragmentos LITERALES del texto; después localizamos cada fragmento por su
posición exacta y descartamos lo que el modelo se «invente» (si no aparece tal
cual en el texto, no se marca). Así evitamos posiciones alucinadas.

No se añaden dependencias: se usa urllib de la biblioteca estándar.
"""

import json
import re
import threading
import time
import urllib.error
import urllib.request

# Endpoints locales habituales que se sondean automáticamente.
ENDPOINTS_HABITUALES = [
    ("http://127.0.0.1:11434", "Ollama"),
    ("http://127.0.0.1:1234", "LM Studio"),
]

# Tipos que el LLM puede devolver → categoría interna de AnoniPRO.
TIPO_A_CATEGORIA = {
    "persona": "persona",
    "paciente": "persona",
    "familiar": "persona",
    "sanitario": "sanitario",
    "profesional": "sanitario",
    "medico": "sanitario",
    "centro": "centro",
    "hospital": "centro",
    "servicio": "servicio_unidad",
    "direccion": "direccion",
    "localidad": "localidad",
    "lugar": "localidad",
    "telefono": "telefono",
    "email": "email",
    "fecha": "fecha",
}

CONFIANZA_CAPA3 = 0.5  # el LLM es una sugerencia; las capas 1-2 tienen prioridad

_PROMPT_SISTEMA = (
    "Eres un revisor de privacidad de documentos clínicos en español. "
    "Tu tarea es encontrar DATOS PERSONALES que puedan identificar a alguien "
    "(pacientes, familiares, profesionales sanitarios, centros, direcciones, "
    "localidades, teléfonos, correos y fechas concretas). "
    "Devuelve EXCLUSIVAMENTE un JSON válido, sin explicaciones, con esta forma:\n"
    '{"entidades": [{"texto": "<fragmento EXACTO copiado del texto>", "tipo": "<uno de: '
    "persona, sanitario, centro, servicio, direccion, localidad, telefono, email, fecha>\"}]}\n"
    "Reglas estrictas:\n"
    "- 'texto' debe ser una copia LITERAL y exacta de una parte del texto (mismas letras y tildes).\n"
    "- No inventes datos ni normalices; si no estás seguro de que algo identifica a una persona, no lo incluyas.\n"
    "- No incluyas términos médicos, diagnósticos, fármacos ni valores de laboratorio.\n"
    "- Si no hay datos personales, devuelve {\"entidades\": []}."
)


# ── configuración en memoria (un solo proceso) ─────────────────────────────
class ConfigCapa3:
    def __init__(self):
        self.activa = False
        self.endpoint = ""       # p. ej. http://127.0.0.1:11434
        self.modelo = ""
        self.timeout = 60        # segundos por llamada
        self._lock = threading.Lock()

    def actualizar(self, activa=None, endpoint=None, modelo=None, timeout=None):
        with self._lock:
            if activa is not None:
                self.activa = bool(activa)
            if endpoint is not None:
                self.endpoint = _normalizar_base(endpoint)
            if modelo is not None:
                self.modelo = modelo
            if timeout is not None:
                self.timeout = int(timeout)

    def como_dict(self):
        return {
            "activa": self.activa,
            "endpoint": self.endpoint,
            "modelo": self.modelo,
            "timeout": self.timeout,
        }

    @property
    def lista_para_usar(self) -> bool:
        return self.activa and bool(self.endpoint) and bool(self.modelo)


CONFIG = ConfigCapa3()


# ── utilidades HTTP ────────────────────────────────────────────────────────
def _normalizar_base(url: str) -> str:
    """Deja la URL base sin barra final ni sufijo /v1."""
    url = (url or "").strip().rstrip("/")
    if url.endswith("/v1"):
        url = url[:-3]
    return url


def _get_json(url: str, timeout: float):
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def _post_json(url: str, cuerpo: dict, timeout: float):
    datos = json.dumps(cuerpo).encode("utf-8")
    req = urllib.request.Request(
        url, data=datos, headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


# ── descubrimiento de endpoints y modelos ──────────────────────────────────
def listar_modelos(base: str, timeout: float = 4) -> list[str]:
    """Modelos disponibles en un endpoint (API OpenAI /v1/models)."""
    base = _normalizar_base(base)
    try:
        data = _get_json(base + "/v1/models", timeout)
        return sorted(m.get("id", "") for m in data.get("data", []) if m.get("id"))
    except Exception:
        # Fallback a la API nativa de Ollama
        try:
            data = _get_json(base + "/api/tags", timeout)
            return sorted(m.get("name", "") for m in data.get("models", []) if m.get("name"))
        except Exception:
            return []


def comprobar_disponible(timeout: float = 3) -> bool:
    """Comprobación RÁPIDA de que el endpoint configurado responde.

    Se usa ANTES de analizar un documento: si el servidor no está, se salta la
    capa 3 en todo el documento en lugar de esperar el timeout en cada página.
    """
    if not CONFIG.lista_para_usar:
        return False
    try:
        _get_json(CONFIG.endpoint + "/v1/models", timeout)
        return True
    except Exception:
        try:
            _get_json(CONFIG.endpoint + "/api/tags", timeout)
            return True
        except Exception:
            return False


def detectar_endpoints(extra: str = "") -> list[dict]:
    """Sondea los endpoints habituales (y uno extra opcional) y lista sus modelos."""
    candidatos = list(ENDPOINTS_HABITUALES)
    if extra:
        base = _normalizar_base(extra)
        if base and base not in [c[0] for c in candidatos]:
            candidatos.insert(0, (base, "Configurado"))

    encontrados = []
    for base, tipo in candidatos:
        modelos = listar_modelos(base, timeout=2)
        if modelos:
            encontrados.append({"endpoint": base, "tipo": tipo, "modelos": modelos})
    return encontrados


def probar(base: str, modelo: str, timeout: float = 30) -> dict:
    """Envía una petición mínima real y comprueba que el modelo responde."""
    base = _normalizar_base(base)
    if not base or not modelo:
        return {"ok": False, "error": "Falta la dirección del servidor o el modelo."}
    t0 = time.monotonic()
    try:
        resp = _post_json(
            base + "/v1/chat/completions",
            {
                "model": modelo,
                "messages": [{"role": "user", "content": "Responde solo con la palabra: correcto"}],
                "temperature": 0,
                "stream": False,
                "max_tokens": 10,
            },
            timeout,
        )
        texto = resp["choices"][0]["message"]["content"]
        ms = int((time.monotonic() - t0) * 1000)
        return {"ok": True, "latencia_ms": ms, "respuesta": texto.strip()[:80]}
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return {"ok": False, "error": (
                f"El servidor respondió, pero no encuentra el modelo «{modelo}». "
                "Revisa el nombre o descárgalo con «ollama pull " + modelo + "».")}
        return {"ok": False, "error": f"El servidor devolvió un error {e.code}."}
    except urllib.error.URLError:
        return {"ok": False, "error": (
            "No se pudo conectar con ese servidor. Comprueba que Ollama o LM Studio "
            "está en marcha en esa dirección y que el equipo es accesible desde la red.")}
    except Exception:
        return {"ok": False, "error": "No se pudo completar la prueba con ese servidor."}


# ── revisión de texto ──────────────────────────────────────────────────────
def _extraer_json(contenido: str) -> dict:
    """Extrae el objeto JSON de la respuesta del modelo, tolerando texto alrededor."""
    contenido = contenido.strip()
    # Quita vallas de código ```json … ```
    contenido = re.sub(r"^```(?:json)?|```$", "", contenido, flags=re.MULTILINE).strip()
    try:
        return json.loads(contenido)
    except Exception:
        pass
    m = re.search(r"\{.*\}", contenido, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            return {}
    return {}


def revisar_texto(texto: str, categorias_activas: set[str]) -> list[dict]:
    """Pide al LLM datos personales y los devuelve como detecciones (capa 3).

    Solo se conservan los fragmentos que aparecen LITERALMENTE en el texto y cuya
    categoría esté activa. Si el endpoint falla, devuelve [] (nunca rompe el flujo).
    """
    if not CONFIG.lista_para_usar or not texto.strip():
        return []

    try:
        resp = _post_json(
            CONFIG.endpoint + "/v1/chat/completions",
            {
                "model": CONFIG.modelo,
                "messages": [
                    {"role": "system", "content": _PROMPT_SISTEMA},
                    {"role": "user", "content": texto},
                ],
                "temperature": 0,
                "stream": False,
            },
            CONFIG.timeout,
        )
        contenido = resp["choices"][0]["message"]["content"]
    except Exception:
        return []  # la capa 3 nunca debe tumbar la anonimización

    datos = _extraer_json(contenido)
    entidades = datos.get("entidades", []) if isinstance(datos, dict) else []

    detecciones = []
    texto_bajo = texto.lower()
    for ent in entidades:
        if not isinstance(ent, dict):
            continue
        fragmento = str(ent.get("texto", "")).strip()
        tipo = str(ent.get("tipo", "")).strip().lower()
        categoria = TIPO_A_CATEGORIA.get(tipo)
        if not fragmento or len(fragmento) < 3 or categoria is None:
            continue
        if categoria not in categorias_activas:
            continue
        # Localiza TODAS las apariciones literales del fragmento (case-insensitive)
        inicio = 0
        frag_bajo = fragmento.lower()
        while True:
            pos = texto_bajo.find(frag_bajo, inicio)
            if pos == -1:
                break
            fin = pos + len(fragmento)
            detecciones.append({
                "inicio": pos,
                "fin": fin,
                "texto": texto[pos:fin],
                "categoria": categoria,
                "capa": 3,
                "confianza": CONFIANZA_CAPA3,
                "contexto": texto[max(0, pos - 60): fin + 60].replace("\n", " ").strip(),
                "detector": "llm",
            })
            inicio = fin
    return detecciones
