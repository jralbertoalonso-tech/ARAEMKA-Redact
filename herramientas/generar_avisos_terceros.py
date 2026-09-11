#!/usr/bin/env python3
"""Genera un inventario reproducible de licencias del entorno del portable.

El inventario se crea después de instalar las dependencias y conserva los
archivos LICENSE, COPYING y NOTICE publicados dentro de cada distribución.
"""

from __future__ import annotations

import argparse
from importlib import metadata
from pathlib import Path
import re


NOMBRES_LICENCIA = re.compile(r"^(license|licence|copying|notice)(\.|$)", re.I)


def valor(meta: metadata.PackageMetadata, *claves: str) -> str:
    for clave in claves:
        dato = meta.get(clave)
        if dato:
            return " ".join(dato.split())
    return "No indicada en los metadatos del paquete"


def generar(destino: Path) -> None:
    if destino.exists():
        for archivo in sorted(destino.rglob("*"), reverse=True):
            if archivo.is_file() or archivo.is_symlink():
                archivo.unlink()
            elif archivo.is_dir():
                archivo.rmdir()
    destino.mkdir(parents=True)

    filas: list[tuple[str, str, str, str]] = []
    for dist in sorted(
        metadata.distributions(),
        key=lambda d: (d.metadata.get("Name") or "").casefold(),
    ):
        meta = dist.metadata
        nombre = meta.get("Name") or "paquete-sin-nombre"
        version = dist.version or "desconocida"
        licencia = valor(meta, "License-Expression", "License")
        origen = valor(meta, "Home-page", "Project-URL")
        filas.append((nombre, version, licencia, origen))

        copiados: set[str] = set()
        carpeta_metadatos = Path(getattr(dist, "_path", ""))
        if not carpeta_metadatos.is_dir():
            continue
        for fuente in carpeta_metadatos.rglob("*"):
            if not fuente.is_file():
                continue
            relativa = fuente.relative_to(carpeta_metadatos)
            partes = [p.casefold() for p in relativa.parts]
            base = fuente.name
            if "licenses" not in partes and not NOMBRES_LICENCIA.match(base):
                continue
            if fuente.stat().st_size > 2_000_000:
                continue
            nombre_seguro = re.sub(r"[^A-Za-z0-9._-]+", "_", nombre)
            carpeta = destino / f"{nombre_seguro}-{version}"
            carpeta.mkdir(exist_ok=True)
            salida = carpeta / base
            contador = 2
            while salida.name in copiados or salida.exists():
                salida = carpeta / f"{Path(base).stem}-{contador}{Path(base).suffix}"
                contador += 1
            # No se copian atributos extendidos del entorno de construcción:
            # en macOS pueden incluir cuarentena/provenance y bloquear durante
            # minutos una operación que solo necesita conservar el texto.
            salida.write_bytes(fuente.read_bytes())
            copiados.add(salida.name)

    lineas = [
        "ARAEMKA Redact — inventario de componentes del entorno de construcción",
        "",
        "Nombre\tVersión\tLicencia declarada\tOrigen",
    ]
    lineas.extend("\t".join(fila) for fila in filas)
    lineas.extend(
        [
            "",
            "Este inventario puede incluir herramientas usadas solo durante la construcción.",
            "Los archivos de licencia disponibles se conservan en las subcarpetas.",
        ]
    )
    (destino / "INDICE.txt").write_text("\n".join(lineas) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("destino", type=Path)
    args = parser.parse_args()
    generar(args.destino.resolve())


if __name__ == "__main__":
    main()
