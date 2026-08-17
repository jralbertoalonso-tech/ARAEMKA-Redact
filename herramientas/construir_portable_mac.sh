#!/bin/bash
# Construye el AnoniPRO portable para macOS (Apple Silicon o Intel, según
# dónde se ejecute). Resultado: dist/AnoniPRO/ y un ZIP versionado para esa
# arquitectura. Python y las librerías quedan incluidos; para OCR hace falta
# Tesseract instalado en el Mac de destino (véase LÉEME PRIMERO.txt).
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

ANONIPRO_VERSION=$(PYTHONPATH=backend .venv/bin/python -c "from app.config import VERSION; print(VERSION)")
MAC_ARCH=$(uname -m)
ZIP="AnoniPRO-portable-macos-${MAC_ARCH}-v${ANONIPRO_VERSION}.zip"
ANONIPRO_PYINSTALLER_CONFIG="${TMPDIR:-/tmp}/anonipro-pyinstaller-cache"
mkdir -p "$ANONIPRO_PYINSTALLER_CONFIG"
export PYINSTALLER_CONFIG_DIR="$ANONIPRO_PYINSTALLER_CONFIG"

.venv/bin/pip install --quiet pyinstaller

for MODELO in es_core_news_md en_core_web_md; do
  if ! .venv/bin/python -c "import ${MODELO}" 2>/dev/null; then
    echo "❌ ERROR: falta el modelo ${MODELO}. Instálalo antes de construir." && exit 1
  fi
done

# Iconos de la aplicación (a partir de frontend/icono.svg)
.venv/bin/python herramientas/generar_iconos.py >/dev/null

# Los modelos medianos mantienen NER y evitan incluir cientos de MB de vectores
# que AnoniPRO no necesita. Los hooks oficiales recopilan spaCy y thinc; las
# extensiones compiladas restantes se fuerzan explícitamente.
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
  --collect-all es_core_news_md \
  --collect-all en_core_web_md \
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
ANONIPRO_NO_ABRIR_NAVEGADOR=1 ANONIPRO_PUERTO=8765 ./dist/AnoniPRO/AnoniPRO &
PID=$!
# El primer arranque en frío puede tardar (macOS escanea el binario nuevo):
# hasta 120 s de margen.
ESTADO=""
for i in $(seq 1 120); do
  sleep 1
  ESTADO=$(curl -s -m 2 http://127.0.0.1:8765/api/estado || true)
  if printf '%s' "$ESTADO" | grep -q "\"version\":\"${ANONIPRO_VERSION}\""; then
    kill $PID 2>/dev/null
    wait $PID 2>/dev/null || true
    break
  fi
  if ! kill -0 $PID 2>/dev/null; then
    echo "❌ ERROR: el ejecutable murió al arrancar. No lo distribuyas." && exit 1
  fi
  [ "$i" = 120 ] && kill $PID 2>/dev/null && echo "❌ ERROR: no respondió a tiempo." && exit 1
done
if ! printf '%s' "$ESTADO" | grep -q '"ocr_disponible":true'; then
  echo "❌ ERROR: el paquete arrancó, pero no localizó Tesseract." && exit 1
fi
if ! printf '%s' "$ESTADO" | grep -q '"ocr_espanol":true'; then
  echo "❌ ERROR: Tesseract no dispone del idioma español." && exit 1
fi
if ! printf '%s' "$ESTADO" | grep -q '"ocr_ingles":true'; then
  echo "❌ ERROR: Tesseract no dispone del idioma inglés." && exit 1
fi
echo "✅ El ejecutable ${ANONIPRO_VERSION} arranca; OCR español e inglés disponibles."

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

# ── Guía de una página para quien recibe el paquete ─────────────────────
cat > "dist/AnoniPRO/LÉEME PRIMERO.txt" <<'FIN'
╔══════════════════════════════════════════════════════════════════════╗
║  AnoniPRO — Anonimiza documentos sin que los datos salgan de tu Mac  ║
║  Nodo Local                                                          ║
╚══════════════════════════════════════════════════════════════════════╝

CÓMO ABRIRLO
────────────
  La PRIMERA vez:
     1. Clic DERECHO sobre  «PRIMERA VEZ — Abrir aquí»  →  Abrir  →  Abrir
     2. Si macOS insiste en que la aplicación está dañada (no lo está: es
        que no lleva la firma de Apple), ve a:
            Ajustes del Sistema  →  Privacidad y seguridad
        baja hasta el aviso y pulsa «Abrir igualmente». Vuelve al paso 1.

  Las siguientes veces:
     Doble clic en  «AnoniPRO»

  Se abrirá una ventana negra: ESA VENTANA ES LA APLICACIÓN, déjala
  abierta mientras la uses. El navegador se abre solo en unos segundos
  (la primera vez puede tardar un minuto).

  Para cerrar AnoniPRO: cierra esa ventana negra.


CÓMO SE USA
───────────
  1. Arrastra tu documento (PDF, Word o una imagen) a la ventana.
  2. Elige el perfil según el tipo de documento (clínico, jurídico,
     facturas, personal…) en el panel de la izquierda.
  3. Revisa lo que ha encontrado en el panel de la derecha: desmarca lo
     que NO quieras borrar y añade a mano lo que se haya escapado.
  4. Pulsa «Aplicar redacción» y confirma.
  5. Revisa la comprobación automática, examina el resultado completo y
     descárgalo solo cuando estés conforme.

  Nada se borra sin que tú lo confirmes.


LO QUE DEBES SABER
──────────────────
  · Todo ocurre en TU ordenador. No se envía nada a internet.
  · Los documentos NO se guardan en el disco: se procesan en memoria y
    se borran solos a los 30 minutos.
  · El borrado es real: el dato se elimina del archivo, no se tapa. No
    se puede recuperar copiando ni pegando.
  · Revisa siempre el resultado antes de compartir el documento: ninguna
    herramienta automática es infalible.


AVISO IMPORTANTE SOBRE LOS RESULTADOS
─────────────────────────────────────
  AnoniPRO es una herramienta de apoyo. No garantiza la detección o
  eliminación completa de todos los datos personales. El OCR, los modelos
  lingüísticos y las reglas automáticas pueden omitir información,
  interpretarla incorrectamente o dejar elementos visibles o susceptibles
  de reidentificación.

  La ausencia de avisos automáticos no certifica que no quede ningún dato.
  Revisa íntegramente el resultado antes de compartirlo, publicarlo o usarlo.
  Cuando corresponda, el responsable del tratamiento conserva sus obligaciones
  legales y debe valorar el riesgo y aplicar medidas adicionales adecuadas.

  En la máxima medida permitida por la ley, el autor no responde de daños
  indirectos derivados del uso incorrecto, de la falta de revisión o de usos
  no previstos. No se excluyen responsabilidades ni derechos que legalmente
  no puedan limitarse. Consulta también «AVISO LEGAL.txt».

  Para documentos ESCANEADOS hace falta instalar el lector de textos una
  sola vez. Abre la aplicación Terminal y pega:
      brew install tesseract tesseract-lang
  (Los PDF normales y los Word funcionan sin esto.)


CAMBIAR DE IDIOMA
─────────────────
  Botón  ES / EN  arriba a la derecha.


NO TOQUES
─────────
  La carpeta «_internal» contiene el motor de la aplicación.

──────────────────────────────────────────────────────────────────────
AnoniPRO · Nodo Local · Autor: Dr. José Ramón Alberto Alonso
FIN

cp "AVISO-LEGAL.md" "dist/AnoniPRO/AVISO LEGAL.txt"

# ZIP listo para distribuir (conserva permisos) y suma verificable.
rm -f "$ZIP" "$ZIP.sha256.txt"
ditto -c -k --keepParent dist/AnoniPRO "$ZIP"
SHA256=$(shasum -a 256 "$ZIP" | awk '{print $1}')
printf '%s  %s\n' "$SHA256" "$ZIP" > "$ZIP.sha256.txt"

echo
echo "✅ Portable creado en: dist/AnoniPRO/"
echo "✅ ZIP de distribución: $ZIP"
echo "✅ SHA-256: $SHA256"
echo "   Ejecutable:          dist/AnoniPRO/AnoniPRO"
echo
echo "OCR en el equipo de destino (opcional, solo para escaneados):"
echo "   brew install tesseract tesseract-lang"
