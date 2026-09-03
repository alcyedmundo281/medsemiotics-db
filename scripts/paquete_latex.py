#!/usr/bin/env python3
"""Empaqueta la fuente LuaLaTeX autocontenida del libro.

Empaqueta el proyecto Quarto entero (`build/quarto/`), que es donde `qmd.py`
deja los capítulos y Quarto deja `libro.tex`, junto a las imágenes ya copiadas
y a `refs.bib`. Antes se armaba a mano con el `build/libro.tex` del generador
propio más las imágenes del árbol `assets/`, y el `.tex` traía rutas
`../assets/...` que solo resolvían compilando desde `build/`. Ahora el ZIP es
autocontenido por construcción: se descomprime y compila donde sea.
"""
from __future__ import annotations

import argparse
import os
import sys
import tempfile
import zipfile
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


INSTRUCCIONES = """# Fuente LuaLaTeX de medsemiotics-db

El paquete es autocontenido: `libro.tex` referencia las imágenes por su ruta
relativa (`assets/img/...`) dentro de este mismo directorio.

```bash
lualatex -halt-on-error -interaction=nonstopmode libro.tex
lualatex -halt-on-error -interaction=nonstopmode libro.tex
```

Requiere LuaLaTeX y FreeSerif. El índice escribe símbolos Unicode
estructurales (≥ ≤ → ±) y el preámbulo los compone con fontspec: **no compila
con pdflatex**. **Biber no hace falta**: la bibliografía va ya resuelta y
numerada en el texto, no por biblatex. `refs.bib` viaja igual porque es el
archivo que otros proyectos citan por su `clave_bibtex`.

`libro.tex` lo genera Quarto desde el proyecto de `build/quarto/`; no se edita
a mano. Para regenerarlo: `python scripts/libro.py --salida build/libro.pdf`.
"""


def crear_paquete(raiz: Path, salida: Path):
    raiz = raiz.resolve()
    proyecto = raiz / "build" / "quarto"
    tex = proyecto / "libro.tex"
    if not tex.is_file():
        raise RuntimeError(
            f"falta {tex.relative_to(raiz)}: genera el libro con "
            "`python scripts/libro.py --salida build/libro.pdf` antes de empaquetar"
        )

    salida.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        prefix="medsemiotics-db-latex-", suffix=".zip", dir=salida.parent,
        delete=False,
    ) as temporal:
        temporal_path = Path(temporal.name)
    try:
        # Todo el proyecto salvo lo que Quarto deja como salida: el PDF pesa y
        # se publica aparte, y `_salida/` no forma parte de la fuente.
        archivos = sorted(
            p for p in proyecto.rglob("*")
            if p.is_file() and "_salida" not in p.relative_to(proyecto).parts
        )
        with zipfile.ZipFile(
            temporal_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
        ) as zf:
            prefijo = Path("medsemiotics-db-latex")
            for archivo in archivos:
                zf.write(archivo, (prefijo / archivo.relative_to(proyecto)).as_posix())
            zf.writestr((prefijo / "COMPILAR.md").as_posix(), INSTRUCCIONES)

        with zipfile.ZipFile(temporal_path) as zf:
            error = zf.testzip()
            if error:
                raise RuntimeError(f"entrada ZIP corrupta: {error}")
            nombres = set(zf.namelist())
            esperados = {
                "medsemiotics-db-latex/libro.tex",
                "medsemiotics-db-latex/refs.bib",
                "medsemiotics-db-latex/COMPILAR.md",
            }
            if not esperados.issubset(nombres):
                raise RuntimeError("el ZIP no conserva la estructura compilable")
        os.replace(temporal_path, salida)
        # El temporal nace en 0600; el ZIP es un asset que otros descargan.
        os.chmod(salida, 0o644)
    finally:
        temporal_path.unlink(missing_ok=True)

    return len(archivos), salida.stat().st_size


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--salida", type=Path, default=Path("build/medsemiotics-db-latex.zip")
    )
    parser.add_argument(
        "--raiz", type=Path, default=Path(__file__).resolve().parents[1]
    )
    args = parser.parse_args()
    salida = args.salida if args.salida.is_absolute() else args.raiz / args.salida
    archivos, bytes_ = crear_paquete(args.raiz, salida)
    print(f"✓ Paquete LuaLaTeX: {archivos} archivos · {bytes_:,} bytes")
    print(f"✓ Salida: {salida}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, zipfile.BadZipFile) as exc:
        print(f"ERROR PAQUETE LATEX: {exc}", file=sys.stderr)
        raise SystemExit(1)
