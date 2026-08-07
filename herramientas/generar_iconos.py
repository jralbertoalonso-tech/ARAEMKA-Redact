"""Genera los iconos de la aplicación a partir de `frontend/icono.svg`.

Produce en `frontend/iconos/`:
  - icono.icns   → icono del ejecutable de macOS (PyInstaller --icon)
  - icono.ico    → icono del ejecutable de Windows
  - icono-256.png, icono-32.png … → tamaños sueltos (documentación, web)

Uso:
    .venv/bin/python herramientas/generar_iconos.py
"""

import shutil
import subprocess
import tempfile
from pathlib import Path

import fitz
from PIL import Image

RAIZ = Path(__file__).resolve().parent.parent
SVG = RAIZ / "frontend" / "icono.svg"
SALIDA = RAIZ / "frontend" / "iconos"

# Tamaños que pide macOS para un .icns completo (normal y @2x para pantallas Retina)
TAMANOS_ICNS = [16, 32, 64, 128, 256, 512, 1024]
TAMANOS_ICO = [16, 24, 32, 48, 64, 128, 256]


def render(tam: int, destino: Path):
    """Renderiza el SVG a PNG cuadrado de `tam` píxeles."""
    with fitz.open(str(SVG)) as doc:
        pagina = doc[0]
        zoom = tam / pagina.rect.width
        pix = pagina.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=True)
        pix.save(str(destino))


def crear_icns(tmp: Path) -> bool:
    """Crea el .icns con iconutil (solo disponible en macOS)."""
    if not shutil.which("iconutil"):
        return False
    iconset = tmp / "icono.iconset"
    iconset.mkdir()
    for tam in TAMANOS_ICNS:
        if tam <= 512:
            render(tam, iconset / f"icon_{tam}x{tam}.png")
        if tam >= 32:                      # versiones @2x
            render(tam, iconset / f"icon_{tam // 2}x{tam // 2}@2x.png")
    subprocess.run(["iconutil", "-c", "icns", str(iconset), "-o", str(SALIDA / "icono.icns")],
                   check=True)
    return True


def crear_ico(tmp: Path):
    """Crea el .ico multitamaño para Windows."""
    base = tmp / "base.png"
    render(1024, base)
    imagen = Image.open(base).convert("RGBA")
    imagen.save(SALIDA / "icono.ico", format="ICO",
                sizes=[(t, t) for t in TAMANOS_ICO])


def main():
    SALIDA.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        for tam in (32, 128, 256, 512):
            render(tam, SALIDA / f"icono-{tam}.png")
        crear_ico(tmp)
        hay_icns = crear_icns(tmp)
    print(f"Iconos generados en {SALIDA}:")
    for f in sorted(SALIDA.iterdir()):
        print(f"  · {f.name}  ({f.stat().st_size // 1024} KB)")
    if not hay_icns:
        print("  (el .icns solo puede generarse en macOS; en Windows no hace falta)")


if __name__ == "__main__":
    main()
