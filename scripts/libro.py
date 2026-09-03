#!/usr/bin/env python3
"""Compila el libro del índice en PDF desde el proyecto Quarto.

    python scripts/libro.py --salida build/libro.pdf

Sustituye al generador de LaTeX propio que vivía aquí: ~900 líneas de escape,
longtables, figuras y preámbulo que había que mantener en paralelo al
ensamblado Markdown de `epub.py`. Las dos ediciones ya habían divergido —el
EPUB no tipografiaba `nucleo` ni `balance`—, que es exactamente lo que pasa
cuando dos renderizadores describen el mismo contenido. Ahora las dos salen del
mismo proyecto `build/quarto/` que genera `scripts/qmd.py`.

La fuente LaTeX no es un intermedio desechable: `keep-tex` la deja en
`build/quarto/libro.tex` —no en `build/libro.tex`, que ya no existe— junto a
las imágenes que `qmd.py` copió al proyecto. Ese directorio compila tal cual,
sin depender del checkout:

    cd build/quarto
    lualatex -halt-on-error -interaction=nonstopmode libro.tex

Eso es lo que empaqueta `paquete_latex.py`.

Requiere Quarto y LuaLaTeX. A diferencia del EPUB no hay respaldo con pandoc a
secas: el preámbulo —fontspec con FreeSerif para ≥ → ±, babel en español,
longtable— lo arma Quarto, y reconstruirlo a mano sería volver justo a lo que
este script jubila. **Biber ya no hace falta**: el `.tex` no usa biblatex,
porque la bibliografía se emite ya resuelta y numerada por `banco.Citas`.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import banco  # noqa: E402  (import tras ajustar sys.path)
import qmd  # noqa: E402
from banco import ErrorGeneracion  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def argumentos() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--salida", type=Path, default=Path("build/libro.pdf"))
    parser.add_argument(
        "--proyecto", type=Path, default=Path("build/quarto"),
        help="dónde se deja el proyecto Quarto generado",
    )
    parser.add_argument("--raiz", type=Path, default=Path(__file__).resolve().parents[1])
    return parser.parse_args()


def validar_libro(tex: Path, pdf: Path, indice: banco.Indice, informe: dict,
                  plano: str) -> str:
    """Comprueba el .tex y el PDF antes de darlos por buenos.

    El grueso de la verificación va contra el `.tex` a propósito: es texto, se
    inspecciona entero sin dependencias, y todo lo que falte ahí falta también
    en el PDF. Del PDF se comprueba que exista y que no sea un cascarón.
    """
    if not tex.is_file():
        raise ErrorGeneracion(f"Quarto no dejó la fuente LaTeX en {tex}")
    fuente = tex.read_text(encoding="utf-8", errors="replace")
    citacion = informe["citacion"]

    comprobaciones = {
        "citas sin resolver ([?])": "[?]" not in fuente,
        "marcadores TODO": "TODO" not in fuente,
        "DOI": citacion.doi in fuente,
        "licencia": citacion.licencia in fuente,
        "aviso de alcance": "juicio clínico" in fuente,
        "bibliografía": "Bibliografía" in fuente,
        "vocabulario": "Vocabulario" in fuente,
        "fuente FreeSerif": "FreeSerif" in fuente,
    }
    if informe["figuras"]:
        comprobaciones["créditos de imágenes"] = "Créditos de imágenes" in fuente
    fallos = [n for n, correcto in comprobaciones.items() if not correcto]
    if fallos:
        raise ErrorGeneracion(
            "validación editorial del libro fallida: " + ", ".join(fallos)
        )

    for simbolo in ("≥", "≤", "→", "±"):
        if simbolo in plano and simbolo not in fuente:
            raise ErrorGeneracion(
                f"el símbolo Unicode {simbolo!r} no llegó al LaTeX: revisa que "
                "el preámbulo siga usando fontspec con FreeSerif"
            )

    for cond in indice.condiciones_por_archivo.values():
        if cond.get("termino") and cond["termino"] not in fuente:
            raise ErrorGeneracion(
                f"la condición «{cond['termino']}» no aparece en el LaTeX"
            )

    # Cada figura entra por el `archivo_local` declarado, la misma autoridad que
    # usan el EPUB y el índice. Una ruta inventada por el renderizador sería una
    # atribución rota.
    faltantes = [
        medio["archivo_local"]
        for _, medio in informe["figuras_detalle"]
        if not banco.figura_en_latex(Path(medio["archivo_local"]), fuente)
    ]
    if faltantes:
        raise ErrorGeneracion(
            "figuras ausentes del LaTeX: " + ", ".join(sorted(set(faltantes)))
        )

    enlaces = fuente.count(banco.DOMINIO_PUBLICO)
    if enlaces < informe["enlaces"]:
        raise ErrorGeneracion(
            f"faltan enlaces al artículo de medsemiotics: {enlaces} de "
            f"{informe['enlaces']}"
        )

    if not pdf.is_file() or pdf.stat().st_size < 100 * 1024:
        raise ErrorGeneracion("el PDF no existe o es sospechosamente pequeño")
    if pdf.read_bytes()[:5] != b"%PDF-":
        raise ErrorGeneracion("el archivo generado no es un PDF")

    return (
        f"LaTeX y PDF coherentes ({informe['condiciones']} condiciones, "
        f"{informe['figuras']} figuras, {informe['enlaces']} enlaces)"
    )


def main() -> int:
    args = argumentos()
    raiz = args.raiz.resolve()
    salida = args.salida if args.salida.is_absolute() else raiz / args.salida
    proyecto = args.proyecto if args.proyecto.is_absolute() else raiz / args.proyecto

    quarto = shutil.which("quarto")
    if not quarto:
        raise ErrorGeneracion(
            "quarto no está en PATH. El PDF se compila desde el proyecto Quarto; "
            "instálalo desde https://quarto.org/docs/get-started/"
        )
    if not shutil.which("lualatex"):
        raise ErrorGeneracion(
            "lualatex no está en PATH. El índice escribe ≥ ≤ → ± y solo LuaLaTeX "
            "con fontspec los compone sin parchear cada glifo"
        )

    indice = banco.Indice(raiz)
    informe = qmd.generar(indice, raiz, proyecto)
    plano = (proyecto / "libro-plano.md").read_text(encoding="utf-8")

    producido = qmd.render(quarto, proyecto, "pdf", ".pdf")
    tex = proyecto / "libro.tex"
    validacion = validar_libro(tex, producido, indice, informe, plano)

    salida.parent.mkdir(parents=True, exist_ok=True)
    os.replace(producido, salida)

    print(f"✓ Motor: quarto ({quarto}) + lualatex")
    print(f"✓ Proyecto: {proyecto.relative_to(raiz)} "
          f"({len(informe['capitulos'])} capítulos)")
    print(f"✓ Conceptos: {informe['conceptos']}")
    print(f"✓ Condiciones: {informe['condiciones']}")
    print(f"✓ Referencias: {informe['referencias_citadas']} citadas de "
          f"{informe['referencias']}")
    print(f"✓ Figuras: {informe['figuras']}")
    print(f"✓ Fuente LaTeX: {tex.relative_to(raiz)} (compila desde su directorio)")
    print(f"✓ Tamaño: {salida.stat().st_size:,} bytes")
    print(f"✓ Validación interna: {validacion}")
    print(f"✓ Salida: {salida}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ErrorGeneracion, subprocess.CalledProcessError, KeyError, ValueError,
            OSError) as exc:
        print(f"ERROR LIBRO: {exc}", file=sys.stderr)
        raise SystemExit(1)
