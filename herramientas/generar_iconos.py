"""Genera los iconos desde el símbolo maestro definitivo de ARAEMKA.

Produce en `frontend/iconos/`:
  - icono.icns   → icono del ejecutable de macOS (PyInstaller --icon)
  - icono.ico    → icono del ejecutable de Windows
  - icono-256.png, icono-32.png … → tamaños sueltos (documentación, web)
  - frontend/icono.png → maestro transparente usado por la interfaz

Uso:
    .venv/bin/python herramientas/generar_iconos.py
"""

import tempfile
from pathlib import Path

from PIL import Image

RAIZ = Path(__file__).resolve().parent.parent
ORIGEN = RAIZ / "materiales" / "marca" / "definitivo" / "ARAEMKA-simbolo-definitivo-512.png"
ICONO_FRONTEND = RAIZ / "frontend" / "icono.png"
SALIDA = RAIZ / "frontend" / "iconos"

TAMANOS_ICNS = [16, 32, 64, 128, 256, 512, 1024]
TAMANOS_ICO = [16, 24, 32, 48, 64, 128, 256]


def render(tam: int, destino: Path):
    """Redimensiona el maestro PNG cuadrado a `tam` píxeles."""
    with Image.open(ORIGEN) as imagen:
        imagen = imagen.convert("RGBA")
        # `thumbnail()` nunca amplía: al generar el maestro de 1024 px desde
        # el símbolo de 512 px lo dejaba centrado a media escala. El maestro es
        # cuadrado, así que un resize exacto conserva sus proporciones.
        imagen = imagen.resize((tam, tam), Image.Resampling.LANCZOS)
        lienzo = Image.new("RGBA", (tam, tam), (255, 255, 255, 0))
        x = (tam - imagen.width) // 2
        y = (tam - imagen.height) // 2
        lienzo.alpha_composite(imagen, (x, y))
        lienzo.save(destino, format="PNG")


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
        render(1024, ICONO_FRONTEND)
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
