#!/usr/bin/env python3
"""Genera la edición EPUB3 reproducible del índice.

Interfaz contractual:
    python scripts/epub.py --salida build/atlas.epub

Comparte el cargador y los renderizadores de texto con scripts/libro.py — la
misma fuente, otra salida. Ejecuta antes `python scripts/build.py` y no
continúes si reporta errores: este generador vuelve a resolver cada `ref` y
cada `concepto` mientras escribe, y aborta si alguno no existe, pero no repite
el resto de las reglas de integridad.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import libro as motor  # noqa: E402  (import tras ajustar sys.path)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

TITULO = motor.TITULO
SUBTITULO = motor.SUBTITULO
AUTOR = motor.AUTOR
LICENCIA = "CC0 1.0 Universal (dominio público)"
AVISO = (
    "Índice de hechos clínicos verificados: umbrales, códigos y cocientes de "
    "verosimilitud con su fuente. No es material didáctico ni sustituye el "
    "juicio clínico — ver medsemiotics y biosemiotics para la exposición "
    "educativa de este mismo contenido."
)


def version_git(raiz: Path) -> str:
    try:
        return subprocess.run(
            ["git", "describe", "--always", "--dirty"],
            cwd=raiz, check=True, capture_output=True, text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "sin-versión-git"


def cita_markdown(indice: "motor.Indice", ref_id: str, donde: str) -> str:
    """Misma cita que build_bibtex empaqueta, en prosa para el EPUB."""
    registro = indice.referencia(str(ref_id))
    if not registro:
        raise motor.ErrorGeneracion(f"{donde}: cita «{ref_id}», que no está en referencias/")
    autores = registro.get("autores") or []
    firma = str(autores[0]) if autores else ""
    if len(autores) > 1:
        firma += " et al."
    revista = " ".join(str(x) for x in (registro.get("publicacion"), registro.get("anio")) if x)
    if registro.get("volumen"):
        revista += f";{registro['volumen']}"
    if registro.get("paginas"):
        revista += f":{registro['paginas']}"
    identificadores = registro.get("identificadores") or {}
    partes = [p for p in (firma, revista) if p]
    if identificadores.get("pmid"):
        partes.append(f"PMID {identificadores['pmid']}")
    return ". ".join(p.rstrip(".") for p in partes if p) + "."


def entrada_concepto_md(cid: str, concepto: dict) -> str:
    detalle = []
    if concepto.get("sinonimos"):
        detalle.append("sinónimos: " + ", ".join(concepto["sinonimos"]))
    codigos = [(k, v) for k, v in (concepto.get("codigos") or {}).items() if v]
    if codigos:
        detalle.append("códigos: " + ", ".join(f"{k} {v}" for k, v in codigos))
    umbral = concepto.get("umbral")
    if isinstance(umbral, dict) and umbral.get("parametro"):
        cortes = []
        if umbral.get("corte_superior") is not None:
            cortes.append(f"> {umbral['corte_superior']}")
        if umbral.get("corte_inferior") is not None:
            cortes.append(f"< {umbral['corte_inferior']}")
        detalle.append(f"umbral: {umbral['parametro']} {' / '.join(cortes)}")
    texto = " · ".join(detalle)
    linea = f"**{concepto.get('termino') or cid}**"
    if texto:
        linea += f" — {texto}"
    return linea


def seccion_vocabulario(indice: "motor.Indice") -> list[str]:
    partes = ["# Vocabulario", ""]
    ubicados: set[str] = set()
    for raiz_id, titulo in motor.GRUPOS_VOCABULARIO:
        hijos = sorted(
            (cid for cid, c in indice.conceptos.items() if c.get("padre") == raiz_id and cid != raiz_id),
            key=lambda cid: indice.termino(cid),
        )
        if not hijos and raiz_id not in indice.conceptos:
            continue
        partes += [f"## {titulo}", ""]
        if not hijos:
            partes += ["*Sin conceptos hijos todavía.*", ""]
            continue
        for cid in hijos:
            ubicados.add(cid)
            partes.append("- " + entrada_concepto_md(cid, indice.concepto(cid)))
        partes.append("")

    huerfanos = sorted((cid for cid in indice.conceptos if cid not in ubicados), key=lambda cid: indice.termino(cid))
    if huerfanos:
        partes += ["## Otros conceptos", ""]
        for cid in huerfanos:
            partes.append("- " + entrada_concepto_md(cid, indice.conceptos[cid]))
        partes.append("")
    return partes


def filas_signo_md(indice: "motor.Indice", arista: dict, donde: str) -> tuple[list[str], list[str]]:
    """Delega la extracción de datos a libro.filas_de_signo (misma fuente que
    el LaTeX) y solo decide el formato Markdown de la fila/nota."""
    filas, notas_datos = motor.filas_de_signo(indice, arista, donde)
    lineas = []
    for fila in filas:
        citas = [cita_markdown(indice, ref_id, donde) for ref_id in fila.citas]
        lineas.append(f"| {fila.etiqueta} | {fila.rol} | {fila.cociente} | {' '.join(citas)} |")
    notas = [f"- **{etiqueta}.** {texto}" for etiqueta, texto in notas_datos]
    return lineas, notas


def figura_markdown(medio: dict) -> str:
    pie = (
        f"{medio['descripcion']}. {medio['credito']}. "
        f"[{medio['fuente']}]({medio['fuente_url']}). "
        f"[{medio['licencia_img']}]({medio['licencia_url']})."
    )
    return f"![{pie}]({medio['archivo_local']})"


def figuras_de_condicion_md(indice: "motor.Indice", signos: list[dict], donde: str) -> list[str]:
    partes: list[str] = []
    vistos: set[str] = set()
    for arista in signos:
        cid = str(arista.get("concepto") or "")
        if not cid or cid in vistos:
            continue
        concepto = motor.resolver_concepto(indice, cid, donde)
        medio = motor.imagen_de_concepto(indice, concepto, f"{donde} ({concepto.get('termino')})")
        if medio:
            vistos.add(cid)
            partes += [figura_markdown(medio), ""]
    return partes


def seccion_condicion_md(indice: "motor.Indice", archivo: str, condicion: dict) -> list[str]:
    termino = condicion.get("termino") or archivo
    donde = f"{archivo} ({termino})"
    partes = [f"## {termino}", ""]
    if condicion.get("termino_en"):
        partes += [f"*{condicion['termino_en']}*", ""]
    if condicion.get("sinonimos"):
        partes += ["Sinónimos: " + ", ".join(condicion["sinonimos"]) + ".", ""]

    base = condicion.get("probabilidad_base")
    if base is not None:
        if isinstance(base, dict) and base.get("valor") is not None:
            partes.append(f"**Probabilidad base.** {base['valor']}.")
            if base.get("poblacion"):
                partes.append(motor.frase(f"Población: {base['poblacion']}"))
        elif isinstance(base, dict) and base.get("rango"):
            partes.append("**Probabilidad base.** " + "–".join(str(v) for v in base["rango"]) + ".")
        elif not isinstance(base, dict):
            partes.append(f"**Probabilidad base.** {base}.")
        partes.append("")

    factores = condicion.get("factores_riesgo") or []
    if factores:
        partes += ["**Factores de riesgo.**", ""]
        for factor in factores:
            nombre = factor.get("nombre") or factor.get("factor") or factor.get("termino") if isinstance(factor, dict) else factor
            partes.append(f"- {motor.frase(nombre)}")
        partes.append("")

    if condicion.get("signos"):
        partes += ["**Signos.**", "", "| Hallazgo | Rol | Cociente | Fuente |", "|---|---|---|---|"]
        notas_todas: list[str] = []
        for arista in condicion["signos"]:
            filas, notas = filas_signo_md(indice, arista, donde)
            partes += filas
            notas_todas += notas
        partes.append("")
        partes += notas_todas
        partes.append("")
        partes += figuras_de_condicion_md(indice, condicion["signos"], donde)

    alarmas = condicion.get("signos_de_alarma") or []
    if alarmas:
        partes += ["**Signos de alarma.**", ""]
        for arista in alarmas:
            concepto = motor.resolver_concepto(indice, arista.get("concepto"), f"{donde} (signo de alarma)")
            texto = concepto.get("termino")
            if arista.get("nota"):
                texto += ": " + motor.frase(arista["nota"])
            partes.append(f"- {texto}")
        partes.append("")

    reglas = condicion.get("reglas") or []
    if reglas:
        partes += ["**Reglas de clasificación.**", ""]
        for regla in reglas:
            componentes = [indice.termino(str(c)) for c in (regla.get("componentes") or [])]
            partes.append(f"- {regla.get('nombre', '')}: {', '.join(componentes)}.")
        partes.append("")

    escalas = condicion.get("escalas") or []
    for escala in escalas:
        partes += [f"**Escala: {escala.get('nombre', '')}.**", ""]
        for tramo in escala.get("tramos") or []:
            cocientes = []
            if tramo.get("lr_positivo"):
                cocientes.append(f"LR+ {tramo['lr_positivo']}")
            if tramo.get("lr_negativo"):
                cocientes.append(f"LR- {tramo['lr_negativo']}")
            partes.append(f"- **{tramo.get('rango', '')}**: {', '.join(cocientes)}")
        partes.append("")

    discrepancias = condicion.get("discrepancias") or []
    if discrepancias:
        partes += ["**Discrepancias entre fuentes.**", ""]
        for item in discrepancias:
            concepto = motor.resolver_concepto(indice, item.get("concepto"), f"{donde} (discrepancia)")
            partes += [f"*{concepto.get('termino')}.*", ""]
            if item.get("resumen"):
                partes += [motor.frase(item["resumen"]), ""]
            for etiqueta, campo in (("A favor", "a_favor"), ("En contra", "en_contra")):
                lado = item.get(campo) or {}
                if not lado.get("dice"):
                    continue
                cita = f" {cita_markdown(indice, lado['ref'], f'{donde} (discrepancia, {etiqueta})')}" if lado.get("ref") else ""
                partes.append(f"- **{etiqueta}:** {motor.frase(lado['dice'])}{cita}")
            partes.append("")
            if item.get("decision"):
                partes += [motor.frase(item["decision"]), ""]
            if item.get("para_reabrirla"):
                partes += [f"*Para reabrirla: {motor.frase(item['para_reabrirla'])}*", ""]

    no_emitidos = condicion.get("no_emitidos") or []
    if no_emitidos:
        partes += ["**Hallazgos no emitidos, y por qué.**", ""]
        for item in no_emitidos:
            concepto = motor.resolver_concepto(indice, item.get("concepto"), f"{donde} (no emitido)")
            texto = motor.frase(item.get("motivo", ""))
            if item.get("nota"):
                texto += " " + motor.frase(item["nota"])
            partes.append(f"- **{concepto.get('termino')}.** {texto}")
        partes.append("")

    modificadores = condicion.get("modificadores") or []
    if modificadores:
        partes += ["**Modificadores.**", ""]
        for item in modificadores:
            concepto = motor.resolver_concepto(indice, item.get("concepto"), f"{donde} (modificador)")
            texto = motor.frase(item.get("efecto", ""))
            if item.get("nota"):
                texto += " " + motor.frase(item["nota"])
            cita = f" {cita_markdown(indice, item['ref'], f'{donde} (modificador)')}" if item.get("ref") else ""
            partes.append(f"- **{concepto.get('termino')}.** {texto}{cita}")
        partes.append("")

    notas_de_uso = condicion.get("notas_de_uso") or []
    if notas_de_uso:
        partes += ["**Notas de uso.**", ""]
        for nota in notas_de_uso:
            partes.append(f"- {motor.frase(nota)}")
        partes.append("")

    if condicion.get("conclusion_de_la_fuente"):
        partes += ["**Conclusión de la fuente.**", "", motor.frase(condicion["conclusion_de_la_fuente"]), ""]

    if condicion.get("pendiente"):
        partes += ["**Fuera de alcance, por ahora.**", ""]
        for item in condicion["pendiente"]:
            partes.append(f"- {motor.frase(item)}")
        partes.append("")

    return partes


def manuscrito(indice: "motor.Indice", version: str) -> str:
    partes = [
        "# Portadilla", "",
        f"## {TITULO}", "",
        f"**{SUBTITULO}**", "",
        f"{AUTOR}", "",
        f"medsemiotics-db · Compilación {date.today().isoformat()} · versión `{version}`", "",
        "# Créditos, licencia y uso", "",
        f"Autor: {AUTOR}. Idioma: español.", "",
        "Identificador: pendiente (sin DOI asignado todavía).", "",
        f"El conjunto se distribuye bajo {LICENCIA}.", "",
        f"**Aviso:** {AVISO}", "",
    ]
    partes += seccion_vocabulario(indice)

    for clase, titulo in motor.CLASES:
        grupo = [(a, c) for a, c in indice.condiciones_por_archivo.items() if c.get("clase") == clase]
        if not grupo:
            continue
        partes += [f"# {titulo}", ""]
        for archivo, condicion in sorted(grupo, key=lambda kv: kv[1].get("termino", "")):
            partes += seccion_condicion_md(indice, archivo, condicion)

    partes += ["# Bibliografía", ""]
    for clave, ref in sorted(indice.referencias.items(), key=lambda kv: kv[1].get("clave_bibtex", "")):
        cita = cita_markdown(indice, clave, "bibliografía")
        doi = (ref.get("identificadores") or {}).get("doi")
        if doi:
            cita += f" doi:[{doi}](https://doi.org/{doi})"
        partes += [f"- {cita}", ""]

    return "\n".join(partes).rstrip() + "\n"


def estilo(path: Path) -> None:
    path.write_text(
        "body{font-family:FreeSerif,serif;line-height:1.45;color:#17212b}"
        "h1{color:#075f69;page-break-before:always}h2{color:#16485a}"
        "table{border-collapse:collapse;width:100%}"
        "th,td{border:1px solid #ccc;padding:.3em .5em;text-align:left;font-size:.85em}"
        "a{color:#075f69}code{font-family:monospace}",
        encoding="utf-8",
    )


def validar_epub(path: Path, indice: "motor.Indice", figuras: int) -> str:
    if not path.is_file() or path.stat().st_size < 20 * 1024:
        raise motor.ErrorGeneracion("el EPUB no existe o es sospechosamente pequeño")
    with zipfile.ZipFile(path) as zf:
        nombres = zf.namelist()
        if not nombres or nombres[0] != "mimetype":
            raise motor.ErrorGeneracion("mimetype no es la primera entrada del contenedor")
        if zf.getinfo("mimetype").compress_type != zipfile.ZIP_STORED:
            raise motor.ErrorGeneracion("mimetype debe almacenarse sin compresión")
        if zf.read("mimetype") != b"application/epub+zip":
            raise motor.ErrorGeneracion("mimetype EPUB incorrecto")
        if "META-INF/container.xml" not in nombres:
            raise motor.ErrorGeneracion("falta META-INF/container.xml")
        textos = b"".join(zf.read(n) for n in nombres if n.endswith((".xhtml", ".html")))
        comprobaciones = {
            "citas sin resolver ([?])": b"[?]" not in textos,
            "bibliografía final": "Bibliografía".encode() in textos,
        }
        for cond in indice.condiciones_por_archivo.values():
            if cond.get("termino") and cond["termino"].encode() not in textos:
                raise motor.ErrorGeneracion(f"la condición «{cond['termino']}» no aparece en el EPUB")
        fallos = [nombre for nombre, correcto in comprobaciones.items() if not correcto]
        if fallos:
            raise motor.ErrorGeneracion("validación editorial EPUB fallida: " + ", ".join(fallos))
        imagenes = [n for n in nombres if n.lower().endswith((".png", ".jpg", ".jpeg", ".svg", ".webp"))]
        if len(imagenes) < figuras:
            raise motor.ErrorGeneracion(
                f"faltan imágenes incrustadas: esperadas al menos {figuras}, halladas {len(imagenes)}"
            )
    return (
        f"contenedor EPUB3 válido ({len(indice.condiciones_por_archivo)} condiciones, "
        f"{len(indice.conceptos)} conceptos, {figuras} figuras)"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--salida", required=True, type=Path)
    parser.add_argument("--raiz", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()

    raiz = args.raiz.resolve()
    salida = args.salida if args.salida.is_absolute() else raiz / args.salida

    indice = motor.Indice(raiz)
    if not indice.condiciones_por_archivo:
        raise motor.ErrorGeneracion("no hay condiciones/*.yaml: nada que empaquetar todavía")

    pandoc = shutil.which("pandoc")
    if not pandoc:
        raise motor.ErrorGeneracion("pandoc no está instalado o no está disponible en PATH")

    version = version_git(raiz)
    salida.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="epub-", dir=salida.parent) as temporal:
        trabajo = Path(temporal)
        md = trabajo / "indice.md"
        css = trabajo / "epub.css"
        texto_manuscrito = manuscrito(indice, version)
        figuras = texto_manuscrito.count("\n![")
        md.write_text(texto_manuscrito, encoding="utf-8")
        estilo(css)
        temporal_epub = trabajo / "indice.epub"
        comando = [
            pandoc, str(md),
            "--from=gfm", "--to=epub3",
            f"--output={temporal_epub}",
            "--toc", "--toc-depth=2",
            f"--css={css}",
            f"--resource-path={raiz}",
            f"--metadata=title:{TITULO}",
            f"--metadata=subtitle:{SUBTITULO}",
            f"--metadata=author:{AUTOR}",
            "--metadata=lang:es",
            f"--metadata=date:{date.today().isoformat()}",
            f"--metadata=rights:{LICENCIA}",
        ]
        subprocess.run(comando, cwd=raiz, check=True)
        validacion = validar_epub(temporal_epub, indice, figuras)
        os.replace(temporal_epub, salida)

    print(f"✓ Conceptos: {len(indice.conceptos)}")
    print(f"✓ Condiciones: {len(indice.condiciones_por_archivo)}")
    print(f"✓ Referencias: {len(indice.referencias)}")
    print(f"✓ Figuras: {figuras}")
    print(f"✓ Versión: {version} · fecha: {date.today().isoformat()}")
    print(f"✓ Tamaño: {salida.stat().st_size:,} bytes")
    print(f"✓ Validación interna: {validacion}")
    print(f"✓ Salida: {salida}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (motor.ErrorGeneracion, subprocess.CalledProcessError, KeyError, ValueError) as exc:
        print(f"ERROR EPUB: {exc}", file=sys.stderr)
        raise SystemExit(1)
