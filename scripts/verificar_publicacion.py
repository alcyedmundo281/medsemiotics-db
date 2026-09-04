#!/usr/bin/env python3
"""Valida la coherencia entre el índice, sus URLs públicas y sus derivados.

Uso general (CI, y antes de cualquier release):
    python scripts/verificar_publicacion.py

Verificación dirigida después de publicar una condición en medsemiotics:
    python scripts/verificar_publicacion.py --id HM:6001 \\
        --url "https://powersemiotics.com/medsemiotics/post.html?slug=..." \\
        --comprobar-web

Verificación de los derivados, al final del pipeline del libro:
    python scripts/verificar_publicacion.py --verificar-derivados \\
        --epub build/indice.epub

Por qué existe. El índice es proveedor, no publicador: cada condición enlaza a
su artículo en medsemiotics y ese enlace viaja después al EPUB, al PDF y al
paquete LaTeX. Un enlace mal escrito, o una figura que se quedó fuera del
contenedor, no rompe ninguna compilación —sale un libro perfectamente
válido que apunta a una página que no existe o publica una imagen sin su
crédito—. Esto lo convierte en un fallo ruidoso.

`--verificar-derivados` va al final del pipeline a propósito: comprueba
`build/quarto/libro.tex`, que solo existe una vez renderizado el PDF. La
comprobación web (`--comprobar-web`) es deliberadamente opcional, para que un
fallo transitorio de red no convierta la integridad local en una prueba
inestable.
"""
from __future__ import annotations

import argparse
import hashlib
import posixpath
import sys
import urllib.request
from urllib.parse import unquote, urlsplit
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import banco  # noqa: E402  (import tras ajustar sys.path)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

EXTENSIONES_IMAGEN = (".png", ".jpg", ".jpeg", ".svg", ".webp", ".gif")


def validar_url(url: str):
    """El problema con esta URL, o None. No comprueba la red."""
    if not url.startswith(banco.DOMINIO_PUBLICO):
        return f"no usa el dominio público {banco.DOMINIO_PUBLICO}"
    if "?slug=" not in url:
        return "no es un enlace a un artículo (falta «?slug=»)"
    if "/ghost/" in url or "/p/" in url:
        return "apunta al editor o a una vista previa, no al artículo público"
    if url != url.strip() or " " in url:
        return "tiene espacios"
    return None


def validar_urls(indice: banco.Indice, errores: list) -> int:
    """URLs bien formadas y sin repetir. Devuelve cuántas condiciones publican.

    Una URL repetida no es un detalle: significa que dos condiciones distintas
    apuntan al mismo artículo, y el lector del libro llega a la ficha
    equivocada.
    """
    vistas = {}
    publicadas = 0
    for archivo, condicion in indice.condiciones_por_archivo.items():
        url = condicion.get("url") or ""
        if not url:
            continue
        publicadas += 1
        problema = validar_url(url)
        if problema:
            errores.append(f"{archivo}: {problema}")
        if url in vistas:
            errores.append(f"{archivo}: comparte URL con {vistas[url]}")
        else:
            vistas[url] = archivo
    return publicadas


def validar_medios(indice: banco.Indice, errores: list) -> list:
    """Toda imagen del índice, con atribución completa y archivo real.

    Repite el contrato de `build.py` porque aquí se comprueba además contra los
    derivados: sin esta lista no se puede saber qué figuras DEBERÍAN estar
    incrustadas en el EPUB.
    """
    figuras = []
    registros = list(indice.conceptos.items()) + list(indice.condiciones_por_archivo.items())
    for cid, concepto in registros:
        for i, medio in enumerate(concepto.get("medios") or [], 1):
            if medio.get("tipo") != "imagen":
                continue
            faltantes = [c for c in banco.REQUERIDOS_IMAGEN if not medio.get(c)]
            if faltantes:
                errores.append(f"{cid}: medio {i} sin {', '.join(faltantes)}")
                continue
            relativa = Path(medio["archivo_local"])
            ruta = (indice.raiz / relativa).resolve()
            try:
                ruta.relative_to(indice.raiz.resolve())
            except ValueError:
                errores.append(f"{cid}: medio {i} apunta fuera del repositorio")
                continue
            if not ruta.is_file():
                errores.append(f"{cid}: no existe {relativa.as_posix()}")
                continue
            figuras.append((cid, relativa, ruta))
    return figuras


def inspeccionar_epub(epub: Path, errores: list):
    """Huellas de imágenes enlazadas desde XHTML, texto y enlaces clicables."""
    if not epub.is_file():
        errores.append(f"no existe el EPUB {epub}")
        return None, "", set()
    try:
        with zipfile.ZipFile(epub) as zf:
            nombres = zf.namelist()
            huellas, enlaces, textos = set(), set(), []
            for nombre in nombres:
                if not nombre.endswith((".xhtml", ".html")):
                    continue
                pagina = ET.fromstring(zf.read(nombre))
                textos.append(" ".join(pagina.itertext()))
                for elemento in pagina.iter():
                    etiqueta = elemento.tag.rsplit("}", 1)[-1]
                    if etiqueta == "a" and elemento.get("href"):
                        enlaces.add(elemento.get("href"))
                    if etiqueta not in ("img", "image"):
                        continue
                    src = elemento.get("src") or elemento.get("href") or elemento.get("{http://www.w3.org/1999/xlink}href")
                    if not src:
                        continue
                    url = urlsplit(src)
                    if url.scheme or url.netloc:
                        errores.append(f"{nombre}: imagen no incrustada {src}")
                        continue
                    ruta = posixpath.normpath(posixpath.join(posixpath.dirname(nombre), unquote(url.path)))
                    if ruta not in nombres:
                        errores.append(f"{nombre}: imagen enlazada inexistente {src}")
                    else:
                        huellas.add(hashlib.sha256(zf.read(ruta)).digest())
        return huellas, " ".join(textos), enlaces
    except (OSError, zipfile.BadZipFile, ET.ParseError) as exc:
        errores.append(f"EPUB inválido {epub}: {exc}")
        return None, "", set()


def validar_contenido_epub(indice: banco.Indice, epub: Path, errores: list):
    huellas, textos, enlaces = inspeccionar_epub(epub, errores)
    if huellas is None:
        return huellas, textos
    for registros in (indice.conceptos, indice.condiciones_por_archivo):
        for rid, registro in registros.items():
            if rid not in textos:
                errores.append(f"{rid}: código ausente del EPUB")
            if registro.get("url") and registro["url"] not in enlaces:
                errores.append(f"{rid}: URL sin enlace clicable en el EPUB")
            for medio in banco.imagenes_de_registro(indice, registro, rid):
                ruta = indice.raiz / medio["archivo_local"]
                if hashlib.sha256(ruta.read_bytes()).digest() not in huellas:
                    errores.append(f"{rid}: {medio['archivo_local']} no está incrustada y enlazada en el EPUB")
                for campo in ("fuente_url", "licencia_url"):
                    if medio[campo] not in enlaces:
                        errores.append(f"{rid}: {campo} sin enlace clicable en el EPUB")
    for ref in indice.referencias.values():
        ids = ref.get("identificadores") or {}
        esperados = []
        if ids.get("pmid"):
            esperados.append(f"https://pubmed.ncbi.nlm.nih.gov/{ids['pmid']}/")
        if ids.get("doi"):
            esperados.append(f"https://doi.org/{ids['doi']}")
        for url in esperados:
            if url not in enlaces:
                errores.append(f"{ref.get('id')}: referencia sin enlace clicable {url}")
    return huellas, textos


def validar_pdf(indice: banco.Indice, pdf: Path, errores: list) -> None:
    """Comprueba texto y anotaciones de enlace en el PDF final, no solo su .tex."""
    from pypdf import PdfReader

    lector = PdfReader(pdf)
    texto = " ".join(p.extract_text() or "" for p in lector.pages)
    enlaces = set()
    for pagina in lector.pages:
        for anotacion in pagina.get("/Annots") or []:
            accion = anotacion.get_object().get("/A")
            if accion and accion.get("/URI"):
                enlaces.add(str(accion["/URI"]))
    for registros in (indice.conceptos, indice.condiciones_por_archivo):
        for rid, registro in registros.items():
            if rid not in texto:
                errores.append(f"{rid}: código ausente del PDF")
            esperados = [registro["url"]] if registro.get("url") else []
            for medio in banco.imagenes_de_registro(indice, registro, rid):
                esperados += [medio["fuente_url"], medio["licencia_url"]]
            for url in esperados:
                if url not in enlaces:
                    errores.append(f"{rid}: enlace ausente del PDF: {url}")
    for campo, etiqueta in (("nucleo", "Núcleo diagnóstico"), ("balance", "Balance diagnóstico")):
        if any(c.get(campo) for c in indice.condiciones_por_archivo.values()) and etiqueta not in texto:
            errores.append(f"{campo}: ausente del PDF")
    citacion = banco.Citacion(indice.raiz)
    for url in (citacion.doi_url, citacion.licencia_url, f"https://orcid.org/{citacion.orcid}"):
        if url not in enlaces:
            errores.append(f"metadatos: enlace ausente del PDF: {url}")


def validar_derivados(indice: banco.Indice, figuras: list, errores: list,
                      epub: Path = None) -> None:
    """Comprueba que URLs y figuras sobrevivan en cada salida del libro.

    Los binarios EPUB y PDF no se versionan; el EPUB se inspecciona cuando el
    llamador entrega `--epub`. Del PDF se comprueba su fuente, que sí es texto:
    `build/quarto/libro.tex`, la que Quarto deja con `keep-tex` y la que
    empaqueta `paquete_latex.py`.

    Las rutas van sin `../`: las imágenes viven DENTRO del proyecto Quarto,
    copiadas por `qmd.py` con su `archivo_local` intacto, que es lo que hace
    autocontenido al paquete LaTeX.
    """
    raiz = indice.raiz
    proyecto = raiz / "build" / "quarto"
    tex = proyecto / "libro.tex"
    plano = proyecto / "libro-plano.md"

    for ruta in (tex, plano):
        if not ruta.is_file():
            errores.append(
                f"falta derivado {ruta.relative_to(raiz)}: genera el libro con "
                "`python scripts/libro.py` antes de verificar derivados"
            )
    tex_txt = tex.read_text(encoding="utf-8", errors="replace") if tex.is_file() else ""
    plano_txt = (
        plano.read_text(encoding="utf-8", errors="replace") if plano.is_file() else ""
    )

    marcas_epub, textos_epub = (None, "")
    if epub is not None:
        marcas_epub, textos_epub = validar_contenido_epub(indice, epub, errores)

    for archivo, condicion in indice.condiciones_por_archivo.items():
        url = condicion.get("url") or ""
        if not url:
            continue
        for nombre, contenido in (
            ("libro.tex", tex_txt), ("libro-plano.md", plano_txt),
        ):
            if contenido and url not in contenido:
                errores.append(f"{archivo}: su URL no está en {nombre}")

    for cid, relativa, ruta in figuras:
        interna = proyecto / relativa
        if proyecto.is_dir() and not interna.is_file():
            errores.append(
                f"{cid}: {relativa.as_posix()} no se copió al proyecto Quarto"
            )
        if tex_txt and not banco.figura_en_latex(relativa, tex_txt):
            errores.append(f"{cid}: {relativa.as_posix()} no está en libro.tex")
        if marcas_epub is not None:
            if hashlib.sha256(ruta.read_bytes()).digest() not in marcas_epub:
                errores.append(
                    f"{cid}: {relativa.as_posix()} no está incrustada en el EPUB"
                )


def comprobar_web(url: str):
    solicitud = urllib.request.Request(
        url, headers={"User-Agent": "medsemiotics-db-ci/1.0"}
    )
    try:
        with urllib.request.urlopen(solicitud, timeout=20) as respuesta:
            if respuesta.status != 200:
                return f"respondió HTTP {respuesta.status}"
            if not respuesta.geturl().startswith(banco.DOMINIO_PUBLICO):
                return f"redirigió fuera del dominio público: {respuesta.geturl()}"
    except Exception as exc:  # la opción es manual; aquí sí interesa el detalle
        return str(exc)
    return None


def buscar_condicion(indice: banco.Indice, referencia: str):
    """La condición por su código HM: o por el nombre de su archivo."""
    if referencia in indice.condiciones_por_archivo:
        return referencia, indice.condiciones_por_archivo[referencia]
    for archivo, condicion in indice.condiciones_por_archivo.items():
        if str(condicion.get("id")) == referencia or archivo == f"{referencia}.yaml":
            return archivo, condicion
    return None, None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--raiz", type=Path, default=Path(__file__).resolve().parents[1])
    ap.add_argument("--id", dest="condicion_id", help="código HM: de la condición")
    ap.add_argument("--url", help="la URL que debe tener; requiere --id")
    ap.add_argument(
        "--comprobar-web", action="store_true",
        help="además pide la URL por HTTP (opcional: la red no debe romper CI)",
    )
    ap.add_argument(
        "--verificar-derivados", action="store_true",
        help="valida URLs y figuras en libro.tex y en el libro aplanado",
    )
    ap.add_argument(
        "--epub", type=Path,
        help="además verifica que cada figura esté incrustada en ese EPUB",
    )
    ap.add_argument("--pdf", type=Path, help="verifica texto y enlaces del PDF final (requiere pypdf)")
    args = ap.parse_args()

    raiz = args.raiz.resolve()
    indice = banco.Indice(raiz)
    errores: list = []

    publicadas = validar_urls(indice, errores)
    figuras = validar_medios(indice, errores)
    if args.pdf:
        pdf = args.pdf if args.pdf.is_absolute() else raiz / args.pdf
        validar_pdf(indice, pdf, errores)

    if args.verificar_derivados or args.epub:
        epub = args.epub
        if epub is not None and not epub.is_absolute():
            epub = raiz / epub
        validar_derivados(indice, figuras, errores, epub)

    objetivo = None
    if args.condicion_id:
        archivo, condicion = buscar_condicion(indice, args.condicion_id)
        if not condicion:
            errores.append(f"no existe la condición {args.condicion_id}")
        else:
            url = condicion.get("url") or ""
            if not url:
                errores.append(f"{args.condicion_id}: sigue sin URL pública")
            if args.url and url != args.url:
                errores.append(f"{args.condicion_id}: URL {url!r} != {args.url!r}")
            if args.comprobar_web and url:
                problema = comprobar_web(url)
                if problema:
                    errores.append(
                        f"{args.condicion_id}: URL pública inválida: {problema}"
                    )
            objetivo = f"✓ {args.condicion_id} ({archivo}): {url}"
    elif args.url:
        errores.append("--url requiere --id")

    if errores:
        for mensaje in errores:
            print(f"✗ {mensaje}", file=sys.stderr)
        return 1

    if objetivo:
        print(objetivo)
    total = len(indice.condiciones_por_archivo)
    print(
        f"✓ Publicación coherente: {publicadas} de {total} condiciones con URL, "
        f"{len(figuras)} figuras con atribución completa"
    )
    if args.verificar_derivados or args.epub:
        print("✓ Derivados coherentes: libro.tex, libro aplanado"
              + (" y EPUB" if args.epub else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
