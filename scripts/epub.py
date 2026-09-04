#!/usr/bin/env python3
"""Genera la edición EPUB3 reproducible del índice.

Interfaz contractual (la que espera `.github/workflows/libro.yml`):
    python scripts/epub.py --salida build/indice.epub

Este script ya NO ensambla el manuscrito. Esa responsabilidad vive en
`scripts/qmd.py`, que proyecta el índice a un proyecto Quarto book en
`build/quarto/`. Aquí solo se elige el motor, se renderiza y se valida.

Dos motores, un solo manuscrito:

  · `quarto` — el camino previsto. Renderiza el proyecto book completo, y del
    mismo árbol salen el PDF y el HTML con `--to pdf` / `--to html`.
  · `pandoc` — el respaldo. Renderiza `build/quarto/libro-plano.md`, que
    `qmd.py` escribe concatenando LOS MISMOS capítulos. No es una edición
    distinta: es el mismo libro aplanado.

El respaldo existe porque Quarto no está disponible en todos los entornos. Si
las dos salidas difieren en contenido, es un fallo de `qmd.py`, no una variante
editorial aceptable.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import zipfile
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import banco  # noqa: E402  (import tras ajustar sys.path)
import qmd  # noqa: E402
import verificar_publicacion  # noqa: E402
from banco import ErrorGeneracion  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Símbolos estructurales que el índice escribe tal cual porque así se leen en
# la clínica. Solo se exige el que de verdad aparece en el manuscrito: pedirlos
# todos convertiría en fallo que ninguna condición use todavía un `±`.
SIMBOLOS = ("≥", "≤", "→", "±", "–", "·")


def argumentos() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--salida", required=True, type=Path)
    parser.add_argument(
        "--motor", choices=("auto", "quarto", "pandoc"), default="auto",
        help="auto usa quarto si está en PATH y cae a pandoc si no",
    )
    parser.add_argument(
        "--proyecto", type=Path, default=Path("build/quarto"),
        help="dónde se deja el proyecto Quarto generado",
    )
    parser.add_argument("--raiz", type=Path, default=Path(__file__).resolve().parents[1])
    return parser.parse_args()


def elegir_motor(preferido: str):
    """(nombre, ejecutable). Falla con un mensaje accionable si no hay ninguno."""
    quarto = shutil.which("quarto")
    pandoc = shutil.which("pandoc")
    if preferido == "quarto":
        if not quarto:
            raise ErrorGeneracion(
                "se pidió --motor quarto pero quarto no está en PATH. "
                "Instálalo desde https://quarto.org/docs/get-started/ o usa "
                "--motor pandoc."
            )
        return "quarto", quarto
    if preferido == "pandoc":
        if not pandoc:
            raise ErrorGeneracion("se pidió --motor pandoc pero pandoc no está en PATH")
        return "pandoc", pandoc
    if quarto:
        return "quarto", quarto
    if pandoc:
        return "pandoc", pandoc
    raise ErrorGeneracion("no hay motor de render: instala quarto (preferido) o pandoc")


def render_pandoc(ejecutable: str, proyecto: Path, destino: Path, informe: dict) -> Path:
    comando = [
        ejecutable, "libro-plano.md",
        # El lector `markdown` de pandoc es el que usa Quarto, así que los dos
        # motores parsean igual. Con `gfm` se perdían tres cosas: los atributos
        # `{#sec-...}` se filtraban como texto al índice, las listas de
        # definiciones del vocabulario se aplanaban a párrafos sueltos, y el
        # pie de figura se reducía a un `alt=` de texto plano —gfm acepta
        # `implicit_figures` pero la ignora—, de modo que los enlaces de
        # crédito y licencia de cada imagen desaparecían del contenedor.
        "--from=markdown", "--to=epub3",
        f"--output={destino}",
        "--toc", "--toc-depth=2",
        # Nivel 2 = un archivo por condición, que es la unidad de lectura real.
        # Nivel 1 dejaba la parte «Enfermedades» entera en un solo XHTML.
        "--split-level=2",
        "--css=epub.css",
        f"--epub-cover-image={informe['portada']}",
        "--epub-metadata=epub-metadata.xml",
        f"--metadata=title:{banco.TITULO}",
        f"--metadata=subtitle:{banco.SUBTITULO}",
        f"--metadata=author:{banco.AUTOR}",
        "--metadata=lang:es",
        f"--metadata=date:{date.today().isoformat()}",
    ]
    subprocess.run(comando, cwd=proyecto, check=True)
    return destino


def validar_epub(path: Path, indice: banco.Indice, informe: dict, plano: str) -> str:
    """Las garantías editoriales del índice, verificadas sobre el contenedor.

    No dependen del motor: son las mismas para quarto y para pandoc. Incluyen
    lo que no se ve leyendo el texto —DOI y licencia en el OPF, portada
    declarada, figuras con pie clicable y el enlace al artículo de
    medsemiotics— porque son justo las que se pierden sin que nadie lo note.
    """
    citacion = informe["citacion"]
    if not path.is_file() or path.stat().st_size < 20 * 1024:
        raise ErrorGeneracion("el EPUB no existe o es sospechosamente pequeño")
    with zipfile.ZipFile(path) as zf:
        nombres = zf.namelist()
        if not nombres or nombres[0] != "mimetype":
            raise ErrorGeneracion("mimetype no es la primera entrada del contenedor")
        if zf.getinfo("mimetype").compress_type != zipfile.ZIP_STORED:
            raise ErrorGeneracion("mimetype debe almacenarse sin compresión")
        if zf.read("mimetype") != b"application/epub+zip":
            raise ErrorGeneracion("mimetype EPUB incorrecto")
        if "META-INF/container.xml" not in nombres:
            raise ErrorGeneracion("falta META-INF/container.xml")

        textos = b"".join(
            zf.read(n) for n in nombres if n.endswith((".xhtml", ".html"))
        )
        comprobaciones = {
            "citas sin resolver ([?])": b"[?]" not in textos,
            "marcadores TODO": b"TODO" not in textos,
            "DOI": citacion.doi.encode() in textos,
            "licencia": citacion.licencia.encode() in textos,
            "aviso de alcance": "juicio clínico".encode() in textos,
            "bibliografía": "Bibliografía".encode() in textos,
            "vocabulario": b"Vocabulario" in textos,
        }
        if informe["figuras"]:
            comprobaciones["créditos de imágenes"] = (
                "Créditos de imágenes".encode() in textos
            )
        fallos = [n for n, correcto in comprobaciones.items() if not correcto]
        if fallos:
            raise ErrorGeneracion(
                "validación editorial EPUB fallida: " + ", ".join(fallos)
            )

        # Ninguna condición puede faltar: es el contenido por el que se compila.
        for cond in indice.condiciones_por_archivo.values():
            if cond.get("termino") and cond["termino"].encode() not in textos:
                raise ErrorGeneracion(
                    f"la condición «{cond['termino']}» no aparece en el EPUB"
                )

        for simbolo in SIMBOLOS:
            if simbolo in plano and simbolo.encode() not in textos:
                raise ErrorGeneracion(
                    f"el símbolo Unicode {simbolo!r} no quedó incrustado"
                )

        # Figuras reales, no <img> sueltos: el pie lleva los enlaces de crédito
        # y licencia, y con el lector equivocado se aplana a un `alt=` de texto
        # plano sin que falle nada.
        if textos.count(b"<figcaption") < informe["figuras"]:
            raise ErrorGeneracion(
                f"solo {textos.count(b'<figcaption')} de {informe['figuras']} "
                "figuras tienen pie: los enlaces de crédito y licencia se perdieron"
            )

        enlaces = textos.count(banco.DOMINIO_PUBLICO.encode())
        if enlaces < informe["enlaces"]:
            raise ErrorGeneracion(
                f"faltan enlaces al artículo de medsemiotics: {enlaces} de "
                f"{informe['enlaces']}"
            )

        opf = [n for n in nombres if n.endswith(".opf")]
        if not opf:
            raise ErrorGeneracion("el contenedor no declara ningún paquete OPF")
        paquete = zf.read(opf[0]).decode("utf-8")
        metadatos = {
            "DOI en dc:identifier": citacion.doi_url in paquete,
            "licencia con URL en dc:rights": citacion.licencia_url in paquete,
            "portada declarada": 'properties="cover-image"' in paquete,
            "editorial": "<dc:publisher" in paquete,
            "identificador único": paquete.count("<dc:identifier") == 1,
            "descripción": "<dc:description" in paquete,
        }
        ausentes = [n for n, ok in metadatos.items() if not ok]
        if ausentes:
            raise ErrorGeneracion("metadatos EPUB incompletos: " + ", ".join(ausentes))

        if not [n for n in nombres if n.endswith("nav.xhtml")]:
            raise ErrorGeneracion("el contenedor no trae índice de navegación")

    errores = []
    verificar_publicacion.validar_contenido_epub(indice, path, errores)
    if errores:
        raise ErrorGeneracion("; ".join(errores))
    return (
        f"contenedor EPUB3 válido ({informe['condiciones']} condiciones, "
        f"{informe['conceptos']} conceptos, {informe['figuras']} figuras)"
    )


def main() -> int:
    args = argumentos()
    raiz = args.raiz.resolve()
    salida = args.salida if args.salida.is_absolute() else raiz / args.salida
    proyecto = args.proyecto if args.proyecto.is_absolute() else raiz / args.proyecto

    nombre_motor, ejecutable = elegir_motor(args.motor)
    indice = banco.Indice(raiz)
    informe = qmd.generar(indice, raiz, proyecto)
    plano = (proyecto / "libro-plano.md").read_text(encoding="utf-8")

    salida.parent.mkdir(parents=True, exist_ok=True)
    if nombre_motor == "quarto":
        producido = qmd.render(ejecutable, proyecto, "epub", ".epub")
    else:
        producido = render_pandoc(
            ejecutable, proyecto, proyecto / "indice-temporal.epub", informe
        )

    validacion = validar_epub(producido, indice, informe, plano)
    os.replace(producido, salida)

    print(f"✓ Motor: {nombre_motor} ({ejecutable})")
    print(f"✓ Proyecto: {proyecto.relative_to(raiz)} "
          f"({len(informe['capitulos'])} capítulos)")
    print(f"✓ Conceptos: {informe['conceptos']}")
    print(f"✓ Condiciones: {informe['condiciones']}")
    print(f"✓ Referencias: {informe['referencias_citadas']} citadas de "
          f"{informe['referencias']}")
    print(f"✓ Figuras incrustadas: {informe['figuras']} (con pie y enlaces)")
    print(f"✓ Enlaces al artículo en medsemiotics: {informe['enlaces']}")
    print(f"✓ Portada: {informe['portada']}")
    print(f"✓ Versión: {informe['version']} · fecha: {date.today().isoformat()}")
    print(f"✓ Tamaño: {salida.stat().st_size:,} bytes")
    print(f"✓ Validación interna: {validacion}")
    print(f"✓ Salida: {salida}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ErrorGeneracion, subprocess.CalledProcessError, KeyError, ValueError,
            OSError) as exc:
        print(f"ERROR EPUB: {exc}", file=sys.stderr)
        raise SystemExit(1)
