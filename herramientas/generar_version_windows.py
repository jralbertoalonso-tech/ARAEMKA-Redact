"""Genera los metadatos de versión que PyInstaller incrusta en AnoniPRO.exe."""

import re
from pathlib import Path


RAIZ = Path(__file__).resolve().parent.parent
CONFIG = RAIZ / "backend" / "app" / "config.py"
SALIDA = RAIZ / "build" / "version_info_windows.txt"
SALIDA_VERSION = RAIZ / "build" / "VERSION.txt"


def main() -> None:
    texto = CONFIG.read_text(encoding="utf-8")
    coincidencia = re.search(r'^VERSION\s*=\s*"([0-9]+(?:\.[0-9]+){1,3})"', texto, re.MULTILINE)
    if not coincidencia:
        raise SystemExit("No se pudo leer VERSION de backend/app/config.py")
    version = coincidencia.group(1)
    partes = [int(p) for p in version.split(".")]
    partes.extend([0] * (4 - len(partes)))
    version_tupla = ", ".join(str(p) for p in partes[:4])

    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    SALIDA.write_text(
        f"""# UTF-8
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=({version_tupla}),
    prodvers=({version_tupla}),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable(
        u'040904B0',
        [StringStruct(u'CompanyName', u'Nodo Local'),
         StringStruct(u'FileDescription', u'AnoniPRO - anonimización local de documentos'),
         StringStruct(u'FileVersion', u'{version}'),
         StringStruct(u'InternalName', u'AnoniPRO'),
         StringStruct(u'LegalCopyright', u'Copyright (c) Dr. José Ramón Alberto Alonso'),
         StringStruct(u'OriginalFilename', u'AnoniPRO.exe'),
         StringStruct(u'ProductName', u'AnoniPRO'),
         StringStruct(u'ProductVersion', u'{version}')])
    ]),
    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)
""",
        encoding="utf-8",
    )
    SALIDA_VERSION.write_text(version, encoding="ascii")
    print(f"Metadatos de Windows {version}: {SALIDA}")


if __name__ == "__main__":
    main()
