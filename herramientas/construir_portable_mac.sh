#!/bin/bash
# Construye el AnoniPRO portable para macOS (Apple Silicon o Intel, según
# dónde se ejecute). Resultado: dist/AnoniPRO/ — carpeta autocontenida que se
# puede comprimir y llevar a cualquier Mac SIN instalar nada.
#
# Uso (desde la raíz del proyecto):
#   bash herramientas/construir_portable_mac.sh
#
# Nota: PyInstaller NO cross-compila. El portable de Windows debe construirse
# en un Windows con herramientas/construir_portable_windows.bat.

set -e
cd "$(dirname "$0")/.."

echo "── AnoniPRO · construcción del portable (macOS) ──"

if [ ! -d ".venv" ]; then
  echo "Primero prepara el entorno de desarrollo (ver README)." && exit 1
fi

.venv/bin/pip install --quiet pyinstaller

# Iconos de la aplicación (a partir de frontend/icono.svg)
.venv/bin/python herramientas/generar_iconos.py >/dev/null

# --collect-all para spaCy y sus dependencias compiladas: PyInstaller no
# detecta solo los módulos en C (spacy.symbols, thinc, blis…).
# cymem además se fuerza con --add-binary: en la práctica hemos visto que en la
# construcción grande puede quedarse fuera aunque --collect-all lo declare.
CYMEM_SO=$(.venv/bin/python -c "import cymem, glob, os; print(glob.glob(os.path.join(os.path.dirname(cymem.__file__), 'cymem.*.so'))[0])")

.venv/bin/pyinstaller --noconfirm --clean \
  --name AnoniPRO \
  --icon frontend/iconos/icono.icns \
  --onedir \
  --console \
  --paths backend \
  --add-data "frontend:frontend" \
  --collect-all es_core_news_lg \
  --collect-all spacy \
  --collect-all thinc \
  --collect-all blis \
  --collect-all srsly \
  --collect-all preshed \
  --collect-all cymem \
  --collect-all murmurhash \
  --collect-all wasabi \
  --collect-all catalogue \
  --collect-all confection \
  --collect-data presidio_analyzer \
  --collect-submodules uvicorn \
  --collect-submodules app \
  --add-binary "$CYMEM_SO:cymem" \
  --hidden-import cymem \
  --hidden-import cymem.cymem \
  backend/portable_main.py

# ── Aplanar enlaces simbólicos ───────────────────────────────────────────
# PyInstaller crea symlinks internos que se ROMPEN al copiar la carpeta a
# discos exFAT, por la nube, etc. Se convierten todos en archivos reales:
# la carpeta funciona entonces la copies como la copies.
echo "Convirtiendo enlaces simbólicos en archivos reales…"
rsync -a --copy-links dist/AnoniPRO/ dist/AnoniPRO-plano/
rm -rf dist/AnoniPRO
mv dist/AnoniPRO-plano dist/AnoniPRO
RESTAN=$(find dist/AnoniPRO -type l | wc -l | tr -d ' ')
if [ "$RESTAN" != "0" ]; then
  echo "❌ ERROR: quedan $RESTAN enlaces simbólicos. No lo distribuyas." && exit 1
fi

# ── Comprobación automática: el paquete debe contener cymem y ARRANCAR ──
if ! find dist/AnoniPRO/_internal -name 'cymem*.so' | grep -q .; then
  echo "❌ ERROR: cymem no quedó dentro del paquete. No lo distribuyas." && exit 1
fi
echo "Comprobando que el ejecutable arranca…"
ANONIPRO_PUERTO=8765 ./dist/AnoniPRO/AnoniPRO &
PID=$!
# El primer arranque en frío puede tardar (macOS escanea el binario nuevo):
# hasta 120 s de margen.
for i in $(seq 1 120); do
  sleep 1
  if curl -s -m 2 http://127.0.0.1:8765/api/estado | grep -q version; then
    kill $PID 2>/dev/null
    echo "✅ El ejecutable arranca y responde."
    break
  fi
  if ! kill -0 $PID 2>/dev/null; then
    echo "❌ ERROR: el ejecutable murió al arrancar. No lo distribuyas." && exit 1
  fi
  [ "$i" = 120 ] && kill $PID 2>/dev/null && echo "❌ ERROR: no respondió a tiempo." && exit 1
done

# ── Desbloqueador de Gatekeeper para el primer arranque en otro Mac ──────
# Sin firma de Apple, macOS marca la app copiada como «dañada» (cuarentena).
# Este .command la desbloquea y arranca; se usa con clic derecho → Abrir.
cat > "dist/AnoniPRO/PRIMERA VEZ — Abrir aquí.command" <<'FIN'
#!/bin/bash
cd "$(dirname "$0")"
echo "── AnoniPRO · primer arranque ──────────────────────"
echo "Quitando el bloqueo de cuarentena de macOS…"
xattr -dr com.apple.quarantine . 2>/dev/null || true
echo "Hecho. Arrancando AnoniPRO…"
echo "(Deja esta ventana abierta: es la aplicación. El navegador se abre solo.)"
echo "────────────────────────────────────────────────────"
./AnoniPRO
FIN
chmod +x "dist/AnoniPRO/PRIMERA VEZ — Abrir aquí.command"

# Zip listo para distribuir (conserva permisos y enlaces internos)
rm -f AnoniPRO-portable-mac.zip
ditto -c -k --keepParent dist/AnoniPRO AnoniPRO-portable-mac.zip

echo
echo "✅ Portable creado en: dist/AnoniPRO/"
echo "✅ Zip de distribución: AnoniPRO-portable-mac.zip"
echo "   Ejecutable:          dist/AnoniPRO/AnoniPRO"
echo "   Para distribuirlo:   comprime la carpeta dist/AnoniPRO en un .zip"
echo
echo "OCR en el equipo de destino (opcional, solo para escaneados):"
echo "   brew install tesseract tesseract-lang"
