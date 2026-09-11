#!/bin/bash
# ARAEMKA Redact — arranque en macOS (Apple Silicon o Intel).
# Doble clic en este archivo desde Finder, o ejecútalo en Terminal.
# La primera vez crea el entorno y descarga el modelo (necesita internet UNA vez).
# Después funciona sin conexión.

set -e
cd "$(dirname "$0")"

echo "── ARAEMKA Redact ────────────────────────────────────"

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

# 2) Crear el entorno virtual la primera vez.
# La marca .venv/.instalacion-ok solo se escribe si TODO fue bien: si una
# instalación se corta a medias (sin internet, por ejemplo), la próxima vez se
# rehace en vez de arrancar con un entorno roto para siempre.
if [ ! -f ".venv/.instalacion-ok" ]; then
  echo "Primera ejecución: preparando el entorno (tarda unos minutos)…"
  rm -rf .venv
  if ! "$PY" -m venv .venv \
     || ! .venv/bin/pip install --quiet --upgrade pip \
     || ! .venv/bin/pip install --quiet -r backend/requirements.txt \
     || ! .venv/bin/python -m spacy download es_core_news_lg; then
    echo
    echo "❌ La preparación falló (¿sin conexión a internet?)."
    echo "   Comprueba la conexión y vuelve a abrir este archivo: se reintentará."
    rm -rf .venv
    read -n 1 -s -r -p "Pulsa una tecla para cerrar."
    exit 1
  fi
  touch .venv/.instalacion-ok
fi

# 3) Elegir un puerto libre (si el 8080 está ocupado por otro servicio, se usa otro)
PUERTO=8080
if nc -z 127.0.0.1 $PUERTO 2>/dev/null; then
  PUERTO=8090
  while nc -z 127.0.0.1 $PUERTO 2>/dev/null; do PUERTO=$((PUERTO+1)); done
  echo "El puerto 8080 está ocupado; se usará el $PUERTO."
fi

# 4) Arrancar y abrir el navegador cuando el servidor responda de verdad
echo "Iniciando ARAEMKA Redact en http://localhost:$PUERTO …"
(
  for _ in $(seq 1 120); do
    sleep 1
    if curl -s -m 2 "http://127.0.0.1:$PUERTO/api/estado" >/dev/null 2>&1; then
      open "http://localhost:$PUERTO"; break
    fi
  done
) &
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port "$PUERTO" --app-dir backend
