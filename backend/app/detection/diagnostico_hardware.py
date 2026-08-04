"""Módulo de diagnóstico de hardware y recomendación de la capa 3 (LLM local).

Detecta sistema operativo, CPU, RAM y aceleración disponible (Apple Silicon/Metal,
NVIDIA/CUDA o solo CPU) y devuelve una recomendación CONCRETA y accionable de qué
modelo usar para la capa 3, con los comandos exactos de instalación.

Catálogo de modelos actualizado a julio de 2026 (verificado en el desarrollo, no
de memoria): los mejores modelos abiertos pequeños con buen español para
extracción/NER son la familia **Qwen3** (29+ idiomas, español fuerte),
**Gemma 3** (140+ idiomas, muy ligero) y **Llama 3.1/3.2** (español fiable).
La cuantización recomendada para 7-8B es Q4_K_M.
"""

import platform
import shutil
import subprocess

try:
    import psutil
except ImportError:  # psutil es recomendable pero el módulo no debe romperse sin él
    psutil = None


# ── Catálogo de modelos para la capa 3 (Ollama) ────────────────────────────
# ram_min_gb = RAM libre aproximada recomendada para el modelo cuantizado Q4.
MODELOS = {
    "qwen3:8b": {
        "nombre": "Qwen 3 8B",
        "pull": "ollama pull qwen3:8b",
        "ram_min_gb": 10,
        "nota": "El mejor equilibrio en español para extraer datos; recomendado si te sobra RAM.",
    },
    "qwen3:4b": {
        "nombre": "Qwen 3 4B",
        "pull": "ollama pull qwen3:4b",
        "ram_min_gb": 6,
        "nota": "Muy buen español en poco espacio; ideal para equipos de 8-16 GB.",
    },
    "gemma3:4b": {
        "nombre": "Gemma 3 4B",
        "pull": "ollama pull gemma3:4b",
        "ram_min_gb": 5,
        "nota": "Ligero (2,5 GB) y con 140+ idiomas; buena alternativa en equipos justos.",
    },
    "llama3.2:3b": {
        "nombre": "Llama 3.2 3B",
        "pull": "ollama pull llama3.2:3b",
        "ram_min_gb": 4,
        "nota": "El más pequeño con español aceptable; para equipos de 8 GB o con poca RAM libre.",
    },
}


def _ram_total_gb() -> float | None:
    if psutil:
        return round(psutil.virtual_memory().total / 1e9, 1)
    return None


def _ram_disponible_gb() -> float | None:
    if psutil:
        return round(psutil.virtual_memory().available / 1e9, 1)
    return None


def _tiene_gpu_nvidia() -> bool:
    """True si hay una GPU NVIDIA (nvidia-smi disponible y responde)."""
    if not shutil.which("nvidia-smi"):
        return False
    try:
        subprocess.run(["nvidia-smi"], capture_output=True, timeout=3, check=True)
        return True
    except Exception:
        return False


def detectar() -> dict:
    """Detecta el hardware del equipo donde corre la app."""
    so = platform.system()               # 'Darwin' | 'Windows' | 'Linux'
    arch = platform.machine()            # 'arm64' | 'x86_64' | 'AMD64'
    es_apple_silicon = so == "Darwin" and arch in ("arm64", "aarch64")

    if es_apple_silicon:
        aceleracion = "Apple Silicon (Metal)"
    elif _tiene_gpu_nvidia():
        aceleracion = "GPU NVIDIA (CUDA)"
    else:
        aceleracion = "Solo CPU"

    nombre_so = {"Darwin": "macOS", "Windows": "Windows", "Linux": "Linux"}.get(so, so)

    return {
        "sistema": nombre_so,
        "version_so": platform.release(),
        "arquitectura": arch,
        "es_apple_silicon": es_apple_silicon,
        "cpu": platform.processor() or arch,
        "nucleos_fisicos": psutil.cpu_count(logical=False) if psutil else None,
        "nucleos_logicos": psutil.cpu_count() if psutil else None,
        "ram_total_gb": _ram_total_gb(),
        "ram_disponible_gb": _ram_disponible_gb(),
        "aceleracion": aceleracion,
    }


def recomendar(hw: dict | None = None) -> dict:
    """Devuelve una recomendación concreta de capa 3 para este equipo.

    Estructura:
      {
        "resumen": texto para el usuario,
        "puede_local": bool,             # ¿tiene sentido correr el LLM en ESTE equipo?
        "modelo": id o None,
        "modelo_info": {...} o None,
        "pasos": [ {sistema, titulo, comandos:[...]} ],  # instalación paso a paso
        "nota_nas": texto,
      }
    """
    hw = hw or detectar()
    # Para dimensionar el modelo se usa la RAM TOTAL (lo que el equipo puede
    # manejar), no la libre en este instante, que fluctúa con las apps abiertas.
    ram = hw.get("ram_total_gb") or 0
    ram_libre = hw.get("ram_disponible_gb")

    # ── Caso NAS / Linux sin GPU: la capa 3 NO debe correr aquí ──────────────
    es_nas = hw["sistema"] == "Linux" and hw["aceleracion"] == "Solo CPU"
    if es_nas:
        return {
            "resumen": (
                "Este equipo (probablemente el NAS) ejecuta perfectamente las capas 1 y 2, "
                "pero NO conviene correr aquí el LLM: no tiene GPU y sería muy lento. "
                "Delega la capa 3 en otro equipo de tu red (un Mac con Ollama o LM Studio)."
            ),
            "puede_local": False,
            "modelo": None,
            "modelo_info": None,
            "pasos": _pasos_delegar_en_red(),
            "nota_nas": (
                "En «Ajustes de la capa 3» pon la dirección de ese equipo, por ejemplo "
                "http://192.168.1.50:11434 (Ollama) o http://192.168.1.50:1234 (LM Studio). "
                "El NAS le enviará el texto por tu red local; ningún dato sale de casa."
            ),
        }

    # ── Elegir modelo según RAM y aceleración ───────────────────────────────
    if ram >= 10 and (hw["es_apple_silicon"] or hw["aceleracion"].startswith("GPU")):
        modelo = "qwen3:8b"
    elif ram >= 6:
        modelo = "qwen3:4b"
    elif ram >= 4:
        modelo = "llama3.2:3b"
    else:
        modelo = None

    if modelo is None:
        return {
            "resumen": (
                f"Tu equipo tiene poca RAM libre ({ram} GB) para un LLM local con soltura. "
                "Puedes usar solo las capas 1 y 2 (que ya cubren la mayoría de los casos), "
                "o delegar la capa 3 en otro equipo de tu red con más memoria."
            ),
            "puede_local": False,
            "modelo": None,
            "modelo_info": None,
            "pasos": _pasos_delegar_en_red(),
            "nota_nas": "",
        }

    info = MODELOS[modelo]
    lento = hw["aceleracion"] == "Solo CPU"
    resumen = (
        f"Recomendación para tu {hw['sistema']} "
        f"({hw['aceleracion']}, {ram} GB de RAM): usa **{info['nombre']}** con Ollama. "
        f"{info['nota']}"
    )
    if ram_libre is not None and ram_libre < info["ram_min_gb"]:
        resumen += (
            f" Ahora mismo tienes solo {ram_libre} GB libres; cierra algunas apps antes "
            "de usar el modelo, o Ollama lo cargará más lento."
        )
    if lento:
        resumen += (
            " Aviso: sin GPU irá más lento (unos segundos por página); si te resulta pesado, "
            "quédate con las capas 1-2 o delega la capa 3 en un equipo con GPU/Apple Silicon."
        )

    return {
        "resumen": resumen,
        "puede_local": True,
        "modelo": modelo,
        "modelo_info": info,
        "pasos": _pasos_instalar_ollama(hw["sistema"], modelo),
        "nota_nas": "",
    }


def _pasos_instalar_ollama(sistema: str, modelo: str) -> list[dict]:
    """Instrucciones paso a paso para instalar Ollama + el modelo, por sistema."""
    pull = MODELOS[modelo]["pull"]
    if sistema == "macOS":
        return [{
            "sistema": "macOS",
            "titulo": "Instalar Ollama y el modelo en tu Mac",
            "comandos": [
                "# 1) Instala Ollama (si no lo tienes):",
                "brew install ollama    # o descárgalo de https://ollama.com/download",
                "# 2) Arranca el servicio:",
                "ollama serve           # déjalo abierto en una terminal",
                "# 3) Descarga el modelo (una sola vez, necesita internet):",
                pull,
                "# 4) Comprueba que responde:",
                'ollama run ' + modelo.split(":")[0] + ' "Di hola en una palabra"',
            ],
        }]
    if sistema == "Windows":
        return [{
            "sistema": "Windows",
            "titulo": "Instalar Ollama y el modelo en Windows (sin admin)",
            "comandos": [
                ":: 1) Descarga e instala Ollama desde https://ollama.com/download/windows",
                "::    (el instalador no requiere permisos de administrador)",
                ":: 2) Ollama arranca solo como servicio en segundo plano.",
                ":: 3) Abre PowerShell o CMD y descarga el modelo:",
                pull,
                ":: 4) Comprueba que responde:",
                'ollama run ' + modelo.split(":")[0] + ' "Di hola en una palabra"',
            ],
        }]
    return [{
        "sistema": sistema,
        "titulo": "Instalar Ollama y el modelo",
        "comandos": ["curl -fsSL https://ollama.com/install.sh | sh", pull],
    }]


def _pasos_delegar_en_red() -> list[dict]:
    """Instrucciones para apuntar la capa 3 a otro equipo de la red local."""
    return [{
        "sistema": "Equipo con Ollama en tu red (p. ej. un Mac)",
        "titulo": "Permitir que el NAS use el Ollama de otro equipo",
        "comandos": [
            "# En el equipo que tiene Ollama, arráncalo escuchando en la red local:",
            "# macOS/Linux:",
            "OLLAMA_HOST=0.0.0.0:11434 ollama serve",
            "# Windows (PowerShell):",
            '$env:OLLAMA_HOST="0.0.0.0:11434"; ollama serve',
            "# Averigua la IP de ese equipo (macOS): ipconfig getifaddr en0",
            "# Luego, en «Ajustes de la capa 3» de AnoniPRO, pon:",
            "#   http://ESA-IP:11434     (Ollama)",
            "#   http://ESA-IP:1234      (LM Studio)",
        ],
    }]
