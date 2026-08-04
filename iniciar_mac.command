#!/bin/bash
# AnoniPRO — arranque en macOS (Apple Silicon o Intel).
# Doble clic en este archivo desde Finder, o ejecútalo en Terminal.
# La primera vez crea el entorno y descarga el modelo (necesita internet UNA vez).
# Después funciona sin conexión.

set -e
cd "$(dirname "$0")"

echo "── AnoniPRO ──────────────────────────────────────────"

# 1) Buscar Python 3.10+ (macOS trae 3.9, que no nos sirve)
PY=""
for cand in python3.13 python3.12 python3.11 python3.10; do
  if command -v "$cand" >/dev/null 2>&1; then PY="$cand"; break; fi
done
if [ -z "$PY" ]; then
  echo "No se encontró Python 3.10 o superior."
  echo "Instálalo con:  brew install python@3.12"
  echo "(si no tienes Homebrew: https://brew.sh)"
  read -n 1 -s -r -p "Pulsa una tecla para cerrar."
  exit 1
fi

# 2) Crear el entorno virtual la primera vez
if [ ! -d ".venv" ]; then
  echo "Primera ejecución: preparando el entorno (tarda unos minutos)…"
  "$PY" -m venv .venv
  .venv/bin/pip install --quiet --upgrade pip
  .venv/bin/pip install --quiet -r backend/requirements.txt
  echo "Descargando el modelo de detección en español…"
  .venv/bin/python -m spacy download es_core_news_lg
fi

# 3) Arrancar y abrir el navegador
echo "Iniciando AnoniPRO en http://localhost:8080 …"
( sleep 3 && open "http://localhost:8080" ) &
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8080 --app-dir backend
