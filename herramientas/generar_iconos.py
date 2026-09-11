"""Genera los iconos de la aplicación a partir de `frontend/icono.svg`.

Produce en `frontend/iconos/`:
  - icono.icns   → icono del ejecutable de macOS (PyInstaller --icon)
  - icono.ico    → icono del ejecutable de Windows
  - icono-256.png, icono-32.png … → tamaños sueltos (documentación, web)

Uso:
    .venv/bin/python herramientas/generar_iconos.py
"""

import tempfile
from pathlib import Path

import fitz
from PIL import Image

RAIZ = Path(__file__).resolve().parent.parent
SVG = RAIZ / "frontend" / "icono.svg"
SALIDA = RAIZ / "frontend" / "iconos"

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
    """Crea el .icns directamente; evita diferencias entre versiones de iconutil."""
    base = tmp / "base-icns.png"
    render(1024, base)
    imagen = Image.open(base).convert("RGBA")
    imagen.save(SALIDA / "icono.icns", format="ICNS",
                sizes=[(t, t) for t in TAMANOS_ICNS])
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
        print("  (no se pudo generar el .icns; en Windows no hace falta)")


if __name__ == "__main__":
    main()
