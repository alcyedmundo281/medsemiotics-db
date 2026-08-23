#!/usr/bin/env python3
"""Genera el libro del índice: build/libro.tex y build/refs.bib.

Una fuente, dos salidas más (junto con scripts/epub.py). No sustituye a
scripts/build.py, que sigue siendo la única autoridad de validación —
ejecútalo primero y no continúes si reporta errores. Este generador confía en
esa validación para no repetirla entera, pero se niega igual a tipografiar un
dato que no puede resolver: un `ref` o un `concepto` que no exista aborta la
generación en vez de imprimir un hueco.

Se compila con LuaLaTeX, no pdflatex, por la misma razón que biosemiotics (su
plantilla de calidad, sin relación de código): fontspec deja escribir ≥, →, ±
tal cual si algún registro los trae, sin parchear glifo por glifo.

Las figuras viven en `conceptos/*.yaml` bajo `medios`, con el mismo esquema
que exige biosemiotics: descripción, crédito, fuente y su URL, licencia y su
URL, y `archivo_local`. Sin alguno de esos datos, o sin el archivo, la
generación aborta — no se omiten imágenes ni se infiere su atribución.

    python scripts/build.py          # primero: valida
    python scripts/libro.py          # luego: escribe build/libro.tex y refs.bib
    cd build
    lualatex -halt-on-error -interaction=nonstopmode libro.tex
    biber libro
    lualatex -halt-on-error -interaction=nonstopmode libro.tex
    lualatex -halt-on-error -interaction=nonstopmode libro.tex
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

try:
    import yaml
except ImportError:
    sys.exit("Falta PyYAML:  pip install pyyaml")

TITULO = "Índice de Semiótica Clínica"
SUBTITULO = "Conceptos, condiciones y sus cocientes de verosimilitud, verificados"
AUTOR = "Dr. Alcy Edmundo Torres Guerrero"

# Grupos de primer nivel bajo HM:0001, en el orden en que aparecen en el
# vocabulario semilla. Un concepto sin padre reconocido aquí cae en «Otros» en
# vez de perderse — el libro no calla lo que no supo dónde poner.
GRUPOS_VOCABULARIO = [
    ("HM:0100", "Signos vitales"),
    ("HM:0200", "Dolor"),
    ("HM:0300", "Síntomas digestivos"),
    ("HM:0400", "Síntomas respiratorios"),
    ("HM:0500", "Síntomas neurológicos"),
    ("HM:0600", "Signos de exploración"),
    ("HM:0700", "Alteraciones analíticas"),
    ("HM:0800", "Síntomas generales"),
    ("HM:0900", "Hallazgos de imagen"),
    ("HM:1000", "Trastornos (vocabulario)"),
    ("HM:2000", "Procedimientos"),
]

CLASES = [
    ("enfermedad", "Enfermedades"),
    ("sindrome", "Síndromes"),
]

# Caracteres especiales de LaTeX. Mismo mapa que usa el generador de
# biosemiotics: el orden de las claves no importa porque el string original se
# recorre una sola vez, así que una sustitución nunca vuelve a procesarse.
_LATEX_ESPECIALES = {
    "\\": r"\textbackslash{}",
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
    "<": r"\textless{}",
    ">": r"\textgreater{}",
}


def escape_latex(s) -> str:
    if s is None:
        return ""
    return "".join(_LATEX_ESPECIALES.get(c, c) for c in str(s))


def frase(texto) -> str:
    """El índice escribe notas en minúscula y sin punto final; aquí son prosa."""
    limpio = " ".join(str(texto or "").split())
    if not limpio:
        return ""
    return limpio[0].upper() + limpio[1:].rstrip(".") + "."


# ── Carga del índice ──────────────────────────────────────────────────────


class Indice:
    def __init__(self, raiz: Path):
        self.raiz = raiz
        self.conceptos = self._cargar("conceptos")
        self.condiciones_por_archivo = self._cargar("condiciones")
        self.referencias = self._cargar("referencias")

    def _cargar(self, directorio: str) -> dict[str, dict]:
        out = {}
        d = self.raiz / directorio
        for f in sorted(d.glob("*.yaml")):
            datos = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
            clave = datos.get("id") or f.stem
            out[clave] = datos
        return out

    def concepto(self, cid: str) -> dict:
        return self.conceptos.get(cid) or {}

    def termino(self, cid: str) -> str:
        return str(self.concepto(cid).get("termino") or cid)

    def referencia(self, ref_id: str) -> dict:
        return self.referencias.get(ref_id) or {}


class ErrorGeneracion(RuntimeError):
    pass


def resolver_ref(indice: Indice, ref_id, donde: str) -> str:
    """La clave BibTeX de una referencia, o aborta: no hay `\\cite` a un
    registro que no existe. Es la misma regla dura que build.py, repetida
    aquí porque tipografiar un hueco en vez de fallar sería peor que fallar."""
    if not ref_id:
        raise ErrorGeneracion(f"{donde}: cita sin «ref»")
    registro = indice.referencia(str(ref_id))
    if not registro:
        raise ErrorGeneracion(f"{donde}: cita «{ref_id}», que no está en referencias/")
    clave = registro.get("clave_bibtex")
    if not clave:
        raise ErrorGeneracion(f"{donde}: «{ref_id}» no tiene «clave_bibtex»")
    return str(clave)


def resolver_concepto(indice: Indice, cid, donde: str) -> dict:
    if not cid:
        raise ErrorGeneracion(f"{donde}: arista sin «concepto»")
    concepto = indice.concepto(str(cid))
    if not concepto:
        raise ErrorGeneracion(f"{donde}: apunta a concepto inexistente «{cid}»")
    return concepto


# ── Imágenes ──────────────────────────────────────────────────────────────

REQUERIDOS_IMAGEN = (
    "descripcion", "credito", "fuente", "fuente_url", "licencia_img",
    "licencia_url", "archivo_local",
)

DPI_IMPRESION = 150


def _dims_px(path: Path):
    """(ancho, alto) en píxeles leyendo solo la cabecera. Sin Pillow: la CI
    corre esto con solo PyYAML instalado."""
    try:
        with path.open("rb") as f:
            head = f.read(24)
            if head[:8] == b"\x89PNG\r\n\x1a\n":
                import struct
                return struct.unpack(">II", head[16:24])
            if head[:2] == b"\xff\xd8":
                import struct
                f.seek(2)
                b = f.read(1)
                while b:
                    while b == b"\xff":
                        b = f.read(1)
                    if b[0] in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
                                0xC9, 0xCA, 0xCB):
                        f.read(3)
                        h, w = struct.unpack(">HH", f.read(4))
                        return w, h
                    seg = struct.unpack(">H", f.read(2))[0]
                    f.seek(seg - 2, 1)
                    b = f.read(1)
    except Exception:
        pass
    return None


def imagen_de_concepto(indice: Indice, concepto: dict, donde: str) -> dict | None:
    """La primera imagen válida de un concepto, o aborta si trae `medios` con
    metadatos incompletos. build.py ya lo valida; esto repite el mínimo que
    libro.py necesita para no tipografiar una figura sin atribución."""
    for i, medio in enumerate(concepto.get("medios") or [], 1):
        if medio.get("tipo") != "imagen":
            continue
        faltantes = [c for c in REQUERIDOS_IMAGEN if not medio.get(c)]
        if faltantes:
            raise ErrorGeneracion(f"{donde}: medio {i} sin {', '.join(faltantes)}")
        ruta = (indice.raiz / medio["archivo_local"]).resolve()
        if not ruta.is_file():
            raise ErrorGeneracion(f"{donde}: no existe {medio['archivo_local']}")
        return medio
    return None


def figura_latex(indice: Indice, medio: dict) -> str:
    ruta = (indice.raiz / medio["archivo_local"]).resolve()
    relativa = ruta.relative_to(indice.raiz.resolve())
    credito = escape_latex(
        ". ".join(p for p in (medio["credito"], medio["fuente"], medio["licencia_img"]) if p) + "."
    )
    desc = escape_latex(medio["descripcion"])
    dims = _dims_px(ruta)
    if dims:
        ancho_in = dims[0] / DPI_IMPRESION
        spec = (rf"width={ancho_in:.2f}in,max width=0.85\textwidth,"
                r"max height=0.4\textheight,keepaspectratio")
    else:
        spec = r"width=0.85\textwidth,height=0.4\textheight,keepaspectratio"
    # libro.tex se compila dentro de build/, de ahí el '../'.
    return "\n".join([
        r"\begin{figure}[H]",
        r"  \centering",
        rf"  \includegraphics[{spec}]{{../{relativa.as_posix()}}}",
        rf"  \caption{{{desc} \textit{{Fuente: {credito}}}}}",
        r"\end{figure}",
    ])


# ── BibTeX ────────────────────────────────────────────────────────────────


def _bibtex_campo(valor: str) -> str:
    # biblatex tipografía el campo con LaTeX real, así que los caracteres
    # especiales se escapan igual que en el cuerpo del libro.
    return escape_latex(valor)


def entrada_bibtex(ref: dict) -> str:
    autores = " and ".join(str(a) for a in (ref.get("autores") or []))
    identificadores = ref.get("identificadores") or {}
    campos = [
        ("author", autores),
        ("title", ref.get("titulo") or ""),
        ("journal", ref.get("publicacion") or ""),
        ("year", str(ref.get("anio") or "")),
        ("volume", str(ref.get("volumen") or "")),
        ("pages", str(ref.get("paginas") or "")),
        ("doi", identificadores.get("doi") or ""),
    ]
    if identificadores.get("pmid"):
        campos.append(("note", f"PMID: {identificadores['pmid']}"))
    lineas = [f"@article{{{ref['clave_bibtex']},"]
    emitidos = [(k, v) for k, v in campos if v]
    for i, (k, v) in enumerate(emitidos):
        coma = "," if i < len(emitidos) - 1 else ""
        lineas.append(f"  {k} = {{{_bibtex_campo(v)}}}{coma}")
    lineas.append("}")
    return "\n".join(lineas)


def build_bibtex(indice: Indice) -> str:
    entradas = [
        entrada_bibtex(ref)
        for _, ref in sorted(indice.referencias.items(), key=lambda kv: kv[1].get("clave_bibtex", ""))
    ]
    return "\n\n".join(entradas) + "\n"


# ── Vocabulario (conceptos) ──────────────────────────────────────────────


def _codigos_no_nulos(concepto: dict) -> list[tuple[str, str]]:
    return [(k, v) for k, v in (concepto.get("codigos") or {}).items() if v]


def entrada_concepto(cid: str, concepto: dict) -> str:
    termino = escape_latex(concepto.get("termino") or cid)
    partes = [rf"\item[{termino}]"]
    detalle = []
    if concepto.get("sinonimos"):
        detalle.append("sinónimos: " + escape_latex(", ".join(concepto["sinonimos"])))
    codigos = _codigos_no_nulos(concepto)
    if codigos:
        detalle.append("códigos: " + escape_latex(", ".join(f"{k} {v}" for k, v in codigos)))
    umbral = concepto.get("umbral")
    if isinstance(umbral, dict) and umbral.get("parametro"):
        cortes = []
        if umbral.get("corte_superior") is not None:
            cortes.append(f"> {umbral['corte_superior']}")
        if umbral.get("corte_inferior") is not None:
            cortes.append(f"< {umbral['corte_inferior']}")
        detalle.append(
            escape_latex(f"umbral: {umbral['parametro']} {' / '.join(cortes)}")
        )
    texto = " · ".join(detalle) if detalle else ""
    if texto:
        partes.append(texto)
    return " ".join(partes)


def capitulo_vocabulario(indice: Indice) -> list[str]:
    L = [r"\part{Vocabulario}"]
    ubicados: set[str] = set()

    for raiz_id, titulo in GRUPOS_VOCABULARIO:
        hijos = sorted(
            (
                cid
                for cid, c in indice.conceptos.items()
                if c.get("padre") == raiz_id and cid != raiz_id
            ),
            key=lambda cid: indice.termino(cid),
        )
        if not hijos and raiz_id not in indice.conceptos:
            continue
        L.append(f"\n\\chapter{{{escape_latex(titulo)}}}")
        raiz_concepto = indice.concepto(raiz_id)
        if raiz_concepto.get("termino") and raiz_id not in ubicados:
            ubicados.add(raiz_id)
        if not hijos:
            L.append(r"\emph{Sin conceptos hijos todavía.}")
            continue
        L.append(r"\begin{description}")
        for cid in hijos:
            ubicados.add(cid)
            L.append(entrada_concepto(cid, indice.concepto(cid)))
        L.append(r"\end{description}")

    huerfanos = sorted(
        (cid for cid in indice.conceptos if cid not in ubicados),
        key=lambda cid: indice.termino(cid),
    )
    if huerfanos:
        L.append("\n\\chapter{Otros conceptos}")
        L.append(
            r"\emph{Conceptos cuyo padre no está en los grupos de arriba: "
            r"probablemente una condición del vocabulario semilla o un nivel "
            r"intermedio nuevo.}"
        )
        L.append(r"\begin{description}")
        for cid in huerfanos:
            L.append(entrada_concepto(cid, indice.conceptos[cid]))
        L.append(r"\end{description}")

    return L


# ── Condiciones ───────────────────────────────────────────────────────────


# Claves conocidas dentro de una arista (`signos`/`signos_de_alarma`) y de sus
# bloques anidados. Un campo que aparezca aquí y no se maneje en
# `filas_de_signo` seria peor que un error: se leería como si el generador lo
# hubiera considerado. Relevadas con un barrido real de las 16 condiciones
# (ver el comentario de `capitulo_condicion`), no de memoria.
CLAVES_ARISTA_CONOCIDAS = {
    "concepto", "rol", "estado_lr", "lr_positivo", "lr_negativo",
    "motivo", "decision", "nota", "advertencia", "ref", "poblacion",
    "sensibilidad", "especificidad", "ic95_sensibilidad", "ic95_especificidad",
    "efecto", "dispara_si", "sostiene", "odds_ratio",
    "tramos", "sensibilidad_por_diametro", "sensibilidad_por_gravedad",
}
CLAVES_LR_CONOCIDAS = {"valor", "rango", "ic95", "ref", "nota", "umbral_condicion", "umbral", "poblacion"}
CLAVES_TRAMO_CONOCIDAS = {"umbral_condicion", "umbral", "lr_positivo", "ic95", "lr_negativo", "ic95_negativo", "ref", "especificidad", "sensibilidad"}


def _numero(v) -> str:
    return f"{v:g}" if isinstance(v, (int, float)) else str(v)


def _lr_texto(lr: dict, etiqueta: str) -> str:
    """Cociente + IC95 + umbral, en texto plano sin escapar todavía."""
    if lr.get("valor") is not None:
        texto = f"{etiqueta} {_numero(lr['valor'])}"
    elif lr.get("rango"):
        texto = f"{etiqueta} " + "–".join(_numero(v) for v in lr["rango"])
    else:
        return ""
    if lr.get("ic95"):
        texto += f" (IC95% {lr['ic95'][0]}–{lr['ic95'][1]})"
    umbral = lr.get("umbral_condicion") or lr.get("umbral")
    if umbral:
        texto += f" [{umbral}]"
    return texto


class FilaSigno:
    """Una fila de la tabla de signos, en texto plano sin escapar."""

    def __init__(self, etiqueta: str, rol: str, cociente: str, citas: list[str]):
        self.etiqueta = etiqueta
        self.rol = rol
        self.cociente = cociente
        self.citas = citas


def filas_de_signo(
    indice: Indice, arista: dict, donde: str
) -> tuple[list[FilaSigno], list[tuple[str, str]]]:
    """Descompone una arista en filas de tabla + notas (etiqueta, texto).

    Aborta si la arista o alguno de sus bloques anidados (lr, tramo) trae una
    clave que este generador no sabe tipografiar todavía — la alternativa,
    tipografiar solo lo reconocido, perdería el dato en silencio.
    """
    concepto = resolver_concepto(indice, arista.get("concepto"), donde)
    termino = concepto.get("termino")
    rol = str(arista.get("rol") or "")
    estado = arista.get("estado_lr") or ""

    sobrantes = sorted(set(arista) - CLAVES_ARISTA_CONOCIDAS)
    if sobrantes:
        raise ErrorGeneracion(
            f"{donde} ({termino}): clave(s) {', '.join(sobrantes)} sin renderizador en libro.py"
        )

    filas: list[FilaSigno] = []
    tramos = arista.get("tramos")
    if tramos:
        for tramo in tramos:
            sobrantes_t = sorted(set(tramo) - CLAVES_TRAMO_CONOCIDAS)
            if sobrantes_t:
                raise ErrorGeneracion(
                    f"{donde} ({termino}), tramo: clave(s) {', '.join(sobrantes_t)} sin renderizador"
                )
            piezas = []
            if tramo.get("lr_positivo") is not None:
                texto = f"LR+ {_numero(tramo['lr_positivo'])}"
                if tramo.get("ic95"):
                    texto += f" (IC95% {tramo['ic95'][0]}–{tramo['ic95'][1]})"
                piezas.append(texto)
            if tramo.get("lr_negativo") is not None:
                texto = f"LR- {_numero(tramo['lr_negativo'])}"
                if tramo.get("ic95_negativo"):
                    texto += f" (IC95% {tramo['ic95_negativo'][0]}–{tramo['ic95_negativo'][1]})"
                piezas.append(texto)
            if tramo.get("especificidad") is not None:
                piezas.append(f"Sp {tramo['especificidad']:.0%}" if isinstance(tramo["especificidad"], float) else f"Sp {tramo['especificidad']}")
            if tramo.get("sensibilidad") is not None:
                piezas.append(f"Se {tramo['sensibilidad']:.0%}" if isinstance(tramo["sensibilidad"], float) else f"Se {tramo['sensibilidad']}")
            citas = []
            if tramo.get("ref"):
                resolver_ref(indice, tramo["ref"], f"{donde} ({termino}, tramo)")  # valida
                citas.append(str(tramo["ref"]))
            umbral = tramo.get("umbral_condicion") or tramo.get("umbral") or "?"
            filas.append(FilaSigno(f"{termino} ({umbral})", rol, " / ".join(piezas), citas))
    elif estado in ("no_medible", "no_medido"):
        citas = []
        if arista.get("ref"):
            resolver_ref(indice, arista["ref"], donde)  # valida
            citas.append(str(arista["ref"]))
        filas.append(FilaSigno(termino, rol, "no medible" if estado == "no_medible" else "no medido", citas))
    else:
        piezas = []
        citas = []
        for campo, etiqueta_lr in (("lr_positivo", "LR+"), ("lr_negativo", "LR-")):
            bloque = arista.get(campo)
            if not bloque:
                continue
            sobrantes_lr = sorted(set(bloque) - CLAVES_LR_CONOCIDAS)
            if sobrantes_lr:
                raise ErrorGeneracion(
                    f"{donde} ({termino}), {campo}: clave(s) {', '.join(sobrantes_lr)} sin renderizador"
                )
            texto = _lr_texto(bloque, etiqueta_lr)
            if texto:
                piezas.append(texto)
            if bloque.get("ref"):
                resolver_ref(indice, bloque["ref"], f"{donde} ({termino})")  # valida
                if str(bloque["ref"]) not in citas:
                    citas.append(str(bloque["ref"]))
        if arista.get("ref"):
            resolver_ref(indice, arista["ref"], donde)  # valida
            if str(arista["ref"]) not in citas:
                citas.append(str(arista["ref"]))
        cociente = " / ".join(piezas) if piezas else (estado or "—")
        filas.append(FilaSigno(termino, rol, cociente, citas))

    notas: list[tuple[str, str]] = []
    for etiqueta, campo in (("Decisión", "decision"), ("Advertencia", "advertencia"), ("Motivo", "motivo"), ("Nota", "nota")):
        if arista.get(campo):
            notas.append((f"{termino} — {etiqueta}", frase(arista[campo])))

    if arista.get("poblacion"):
        notas.append((f"{termino} — Población", frase(arista["poblacion"])))

    rendimiento = []
    if arista.get("sensibilidad") is not None:
        sens = arista["sensibilidad"]
        texto = f"Se {sens:.0%}" if isinstance(sens, float) and sens <= 1 else f"Se {sens}"
        if arista.get("ic95_sensibilidad"):
            texto += f" (IC95% {arista['ic95_sensibilidad'][0]}–{arista['ic95_sensibilidad'][1]})"
        rendimiento.append(texto)
    if arista.get("especificidad") is not None:
        esp = arista["especificidad"]
        texto = f"Sp {esp:.0%}" if isinstance(esp, float) and esp <= 1 else f"Sp {esp}"
        if arista.get("ic95_especificidad"):
            texto += f" (IC95% {arista['ic95_especificidad'][0]}–{arista['ic95_especificidad'][1]})"
        rendimiento.append(texto)
    if rendimiento:
        notas.append((f"{termino} — Rendimiento", ", ".join(rendimiento) + "."))

    for campo, etiqueta_campo in (
        ("sensibilidad_por_diametro", "Sensibilidad por diámetro"),
        ("sensibilidad_por_gravedad", "Sensibilidad por gravedad"),
    ):
        tramos_sens = arista.get(campo)
        if tramos_sens:
            clave_tramo = "diametro" if campo == "sensibilidad_por_diametro" else "gravedad"
            piezas = [
                f"{t.get(clave_tramo, '?')}: {t.get('sensibilidad')}" for t in tramos_sens
            ]
            notas.append((f"{termino} — {etiqueta_campo}", "; ".join(piezas) + "."))

    return filas, notas


def figuras_de_condicion(indice: Indice, signos: list[dict], donde: str) -> list[str]:
    """Una figura por cada concepto ilustrado entre los signos de la
    condición, en el orden en que aparecen y sin repetir el mismo concepto
    dos veces."""
    L: list[str] = []
    vistos: set[str] = set()
    for arista in signos:
        cid = str(arista.get("concepto") or "")
        if not cid or cid in vistos:
            continue
        concepto = resolver_concepto(indice, cid, donde)
        medio = imagen_de_concepto(indice, concepto, f"{donde} ({concepto.get('termino')})")
        if medio:
            vistos.add(cid)
            L.append(figura_latex(indice, medio))
    return L


def tabla_signos(indice: Indice, signos: list[dict], donde: str) -> list[str]:
    L = [
        r"\begin{longtable}{p{4.2cm}p{2cm}p{5cm}p{1.2cm}}",
        r"\textbf{Hallazgo} & \textbf{Rol} & \textbf{Cociente} & \textbf{Fuente} \\",
        r"\hline",
        r"\endhead",
    ]
    notas_todas: list[tuple[str, str]] = []
    for arista in signos:
        filas, notas = filas_de_signo(indice, arista, donde)
        for fila in filas:
            claves = [resolver_ref(indice, c, donde) for c in fila.citas]
            cita_tex = ", ".join(rf"\cite{{{c}}}" for c in claves)
            L.append(
                f"{escape_latex(fila.etiqueta)} & {escape_latex(fila.rol)} & "
                f"{escape_latex(fila.cociente)} & {cita_tex} \\\\"
            )
        notas_todas += notas
    L.append(r"\end{longtable}")
    if notas_todas:
        L.append(r"\begin{itemize}")
        for etiqueta, texto in notas_todas:
            L.append(rf"\item[{escape_latex(etiqueta)}.] {escape_latex(texto)}")
        L.append(r"\end{itemize}")
    return L


def bloque_probabilidad_base(indice: Indice, condicion: dict, donde: str) -> list[str]:
    base = condicion.get("probabilidad_base")
    if base is None:
        return []
    L = [r"\paragraph{Probabilidad base.}"]
    if isinstance(base, dict):
        if base.get("valor") is not None:
            texto = f"{base['valor']:.0%}" if isinstance(base["valor"], float) and base["valor"] <= 1 else str(base["valor"])
            L[-1] += " " + escape_latex(texto) + "."
        elif base.get("rango"):
            L[-1] += " " + escape_latex("–".join(str(v) for v in base["rango"])) + "."
        if base.get("poblacion"):
            L.append(escape_latex(frase(f"Población: {base['poblacion']}")))
        if base.get("ref"):
            clave = resolver_ref(indice, base["ref"], f"{donde} (probabilidad base)")
            L.append(rf"\cite{{{clave}}}")
    else:
        L[-1] += " " + escape_latex(str(base)) + "."
    return L


def bloque_factores_riesgo(condicion: dict) -> list[str]:
    factores = condicion.get("factores_riesgo") or []
    if not factores:
        return []
    L = [r"\paragraph{Factores de riesgo.}", r"\begin{itemize}"]
    for factor in factores:
        if isinstance(factor, dict):
            nombre = factor.get("nombre") or factor.get("factor") or factor.get("termino") or ""
            L.append(rf"\item {escape_latex(frase(nombre))}")
        else:
            L.append(rf"\item {escape_latex(frase(factor))}")
    L.append(r"\end{itemize}")
    return L


def bloque_nucleo_balance(indice: Indice, condicion: dict, donde: str) -> list[str]:
    L = []
    nucleo = condicion.get("nucleo")
    if isinstance(nucleo, dict):
        L.append(r"\paragraph{Núcleo diagnóstico.}")
        partes = []
        for campo, etiqueta in (("requiere", "requiere"), ("y_al_menos_uno_de", "y al menos uno de")):
            terminos = [indice.termino(str(c)) for c in (nucleo.get(campo) or [])]
            if terminos:
                partes.append(f"{etiqueta}: " + ", ".join(terminos))
        L[-1] += " " + escape_latex("; ".join(partes)) + "."
        if nucleo.get("ref"):
            clave = resolver_ref(indice, nucleo["ref"], f"{donde} (núcleo)")
            L.append(rf"\cite{{{clave}}}")

    balance = condicion.get("balance")
    if isinstance(balance, dict):
        L.append(r"\paragraph{Balance diagnóstico.}")
        L.append(r"\begin{itemize}")
        for nombre, regla in balance.items():
            if nombre in ("ref", "nota", "fuente") or not isinstance(regla, dict):
                continue
            campos = ", ".join(f"{k}: {v}" for k, v in regla.items())
            L.append(rf"\item \textbf{{{escape_latex(nombre)}}}: {escape_latex(campos)}")
        L.append(r"\end{itemize}")
        if balance.get("ref"):
            clave = resolver_ref(indice, balance["ref"], f"{donde} (balance)")
            L.append(rf"\cite{{{clave}}}")

    return L


def bloque_signos_de_alarma(indice: Indice, condicion: dict, donde: str) -> list[str]:
    alarmas = condicion.get("signos_de_alarma") or []
    if not alarmas:
        return []
    L = [r"\paragraph{Signos de alarma.}", r"\begin{itemize}"]
    for arista in alarmas:
        concepto = resolver_concepto(indice, arista.get("concepto"), f"{donde} (signo de alarma)")
        texto = escape_latex(concepto.get("termino"))
        if arista.get("nota"):
            texto += ": " + escape_latex(frase(arista["nota"]))
        L.append(rf"\item {texto}")
        if arista.get("ref"):
            clave = resolver_ref(indice, arista["ref"], f"{donde} (signo de alarma)")
            L.append(rf"\cite{{{clave}}}")
    L.append(r"\end{itemize}")
    return L


def bloque_reglas(indice: Indice, condicion: dict, donde: str) -> list[str]:
    reglas = condicion.get("reglas") or []
    if not reglas:
        return []
    L = [r"\paragraph{Reglas de clasificación.}"]
    for regla in reglas:
        componentes = [indice.termino(str(c)) for c in (regla.get("componentes") or [])]
        L.append(escape_latex(f"{regla.get('nombre', '')}: {', '.join(componentes)}."))
        if regla.get("criterio"):
            L.append(escape_latex(frase(regla["criterio"])))
        if regla.get("decision"):
            L.append(escape_latex(frase(regla["decision"])))
        if regla.get("ref"):
            clave = resolver_ref(indice, regla["ref"], f"{donde} (regla)")
            L.append(rf"\cite{{{clave}}}")
    return L


def bloque_escalas(condicion: dict) -> list[str]:
    escalas = condicion.get("escalas") or []
    if not escalas:
        return []
    L = []
    for escala in escalas:
        L.append(rf"\paragraph{{Escala: {escape_latex(escala.get('nombre', ''))}.}}")
        L.append(r"\begin{itemize}")
        for tramo in escala.get("tramos") or []:
            cocientes = []
            if tramo.get("lr_positivo"):
                cocientes.append(f"LR+ {tramo['lr_positivo']}")
            if tramo.get("lr_negativo"):
                cocientes.append(f"LR- {tramo['lr_negativo']}")
            L.append(
                rf"\item \textbf{{{escape_latex(tramo.get('rango', ''))}}}: "
                + escape_latex(", ".join(cocientes))
            )
        L.append(r"\end{itemize}")
        if escala.get("decision"):
            L.append(escape_latex(frase(escala["decision"])))
    return L


def bloque_no_emitidos(indice: Indice, condicion: dict, donde: str) -> list[str]:
    items = condicion.get("no_emitidos") or []
    if not items:
        return []
    L = [r"\paragraph{Hallazgos no emitidos, y por qué.}", r"\begin{itemize}"]
    for item in items:
        concepto = resolver_concepto(indice, item.get("concepto"), f"{donde} (no emitido)")
        texto = escape_latex(frase(item.get("motivo", "")))
        if item.get("nota"):
            texto += " " + escape_latex(frase(item["nota"]))
        L.append(rf"\item[{escape_latex(concepto.get('termino'))}.] {texto}")
    L.append(r"\end{itemize}")
    return L


def bloque_discrepancias(indice: Indice, condicion: dict, donde: str) -> list[str]:
    items = condicion.get("discrepancias") or []
    if not items:
        return []
    L = [r"\paragraph{Discrepancias entre fuentes.}"]
    for item in items:
        concepto = resolver_concepto(indice, item.get("concepto"), f"{donde} (discrepancia)")
        L.append(rf"\subparagraph{{{escape_latex(concepto.get('termino'))}.}}")
        if item.get("resumen"):
            L.append(escape_latex(frase(item["resumen"])))
        L.append(r"\begin{itemize}")
        for etiqueta, campo in (("A favor", "a_favor"), ("En contra", "en_contra")):
            lado = item.get(campo) or {}
            if not lado.get("dice"):
                continue
            cita_tex = ""
            if lado.get("ref"):
                clave = resolver_ref(indice, lado["ref"], f"{donde} (discrepancia, {etiqueta})")
                cita_tex = rf" \cite{{{clave}}}"
            L.append(rf"\item \textbf{{{etiqueta}}}: {escape_latex(frase(lado['dice']))}{cita_tex}")
        L.append(r"\end{itemize}")
        if item.get("decision"):
            L.append(escape_latex(frase(item["decision"])))
        if item.get("para_reabrirla"):
            L.append(r"\emph{Para reabrirla: " + escape_latex(frase(item["para_reabrirla"])) + "}")
    return L


def bloque_modificadores(indice: Indice, condicion: dict, donde: str) -> list[str]:
    items = condicion.get("modificadores") or []
    if not items:
        return []
    L = [r"\paragraph{Modificadores.}", r"\begin{itemize}"]
    for item in items:
        concepto = resolver_concepto(indice, item.get("concepto"), f"{donde} (modificador)")
        texto = escape_latex(frase(item.get("efecto", "")))
        if item.get("nota"):
            texto += " " + escape_latex(frase(item["nota"]))
        cita_tex = ""
        if item.get("ref"):
            clave = resolver_ref(indice, item["ref"], f"{donde} (modificador)")
            cita_tex = rf" \cite{{{clave}}}"
        L.append(rf"\item[{escape_latex(concepto.get('termino'))}.] {texto}{cita_tex}")
    L.append(r"\end{itemize}")
    return L


def bloque_notas_de_uso(condicion: dict) -> list[str]:
    notas = condicion.get("notas_de_uso") or []
    if not notas:
        return []
    L = [r"\paragraph{Notas de uso.}", r"\begin{itemize}"]
    for nota in notas:
        L.append(rf"\item {escape_latex(frase(nota))}")
    L.append(r"\end{itemize}")
    return L


CAMPOS_CONOCIDOS = {
    "id", "tipo", "clase", "termino", "termino_en", "sinonimos", "codigos",
    "probabilidad_base", "factores_riesgo", "signos", "procedencia",
    "conclusion_de_la_fuente", "pendiente", "reglas", "escalas",
    "signos_de_alarma", "nucleo", "balance",
    # Declarativamente honestos, pero no clínicos: se tipografían igual con el
    # renderizador genérico para no perderlos.
    "no_emitidos", "discrepancias", "modificadores", "notas_de_uso",
}


def capitulo_condicion(indice: Indice, archivo: str, condicion: dict) -> list[str]:
    termino = condicion.get("termino") or archivo
    donde = f"{archivo} ({termino})"
    L = [f"\n\\chapter{{{escape_latex(termino)}}}", f"\\label{{cond:{condicion.get('id', archivo)}}}"]

    if condicion.get("termino_en"):
        L.append(rf"\emph{{{escape_latex(condicion['termino_en'])}}}")
    if condicion.get("sinonimos"):
        L.append(escape_latex("Sinónimos: " + ", ".join(condicion["sinonimos"])) + ".")

    L += bloque_probabilidad_base(indice, condicion, donde)
    L += bloque_factores_riesgo(condicion)
    L += bloque_nucleo_balance(indice, condicion, donde)

    if condicion.get("signos"):
        L.append(r"\paragraph{Signos.}")
        L += tabla_signos(indice, condicion["signos"], donde)
        L += figuras_de_condicion(indice, condicion["signos"], donde)

    L += bloque_signos_de_alarma(indice, condicion, donde)
    L += bloque_reglas(indice, condicion, donde)
    L += bloque_escalas(condicion)

    L += bloque_discrepancias(indice, condicion, donde)
    L += bloque_no_emitidos(indice, condicion, donde)
    L += bloque_modificadores(indice, condicion, donde)
    L += bloque_notas_de_uso(condicion)

    if condicion.get("conclusion_de_la_fuente"):
        L.append(r"\paragraph{Conclusión de la fuente.}")
        L.append(escape_latex(frase(condicion["conclusion_de_la_fuente"])))

    if condicion.get("pendiente"):
        L.append(r"\paragraph{Fuera de alcance, por ahora.}")
        L.append(r"\begin{itemize}")
        for item in condicion["pendiente"]:
            L.append(rf"\item {escape_latex(frase(item))}")
        L.append(r"\end{itemize}")

    sobrantes = sorted(set(condicion) - CAMPOS_CONOCIDOS)
    if sobrantes:
        raise ErrorGeneracion(
            f"{donde}: campo(s) {', '.join(sobrantes)} sin renderizador. "
            f"Añádelo a libro.py en el mismo cambio que lo emite el índice."
        )

    return L


def parte_condiciones(indice: Indice) -> list[str]:
    L = []
    for clase, titulo in CLASES:
        grupo = [
            (archivo, c)
            for archivo, c in indice.condiciones_por_archivo.items()
            if c.get("clase") == clase
        ]
        if not grupo:
            continue
        L.append(f"\n\\part{{{escape_latex(titulo)}}}")
        for archivo, condicion in sorted(grupo, key=lambda kv: kv[1].get("termino", "")):
            L += capitulo_condicion(indice, archivo, condicion)
    return L


# ── Documento completo ────────────────────────────────────────────────────


def build_latex(indice: Indice, autor: str = AUTOR) -> str:
    L = [
        r"\documentclass[11pt]{book}",
        r"\usepackage{fontspec}",
        r"\setmainfont{FreeSerif}",
        r"\usepackage[spanish]{babel}",
        r"\usepackage{longtable}",
        r"\usepackage{array}",
        r"\usepackage{graphicx}",
        r"\usepackage{float}",
        r"\usepackage[export]{adjustbox}",  # habilita 'max width' en includegraphics
        r"\usepackage[hidelinks]{hyperref}",
        r"\usepackage[backend=biber,style=numeric]{biblatex}",
        r"\addbibresource{refs.bib}",
        rf"\title{{{escape_latex(TITULO)}\\\large {escape_latex(SUBTITULO)}}}",
        rf"\author{{{escape_latex(autor)}}}",
        r"\begin{document}",
        r"\maketitle",
        r"\tableofcontents",
    ]
    L += capitulo_vocabulario(indice)
    L += parte_condiciones(indice)
    L += [r"\printbibliography", r"\end{document}"]
    return "\n".join(L) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raiz", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--build-dir", type=Path, default=None)
    args = parser.parse_args()

    raiz = args.raiz.resolve()
    build_dir = (args.build_dir or raiz / "build").resolve()
    build_dir.mkdir(parents=True, exist_ok=True)

    indice = Indice(raiz)
    if not indice.condiciones_por_archivo:
        raise ErrorGeneracion("no hay condiciones/*.yaml: nada que tipografiar todavía")

    tex = build_latex(indice)
    (build_dir / "libro.tex").write_text(tex, encoding="utf-8")

    bib = build_bibtex(indice)
    (build_dir / "refs.bib").write_text(bib, encoding="utf-8")

    print(f"✓ Conceptos: {len(indice.conceptos)}")
    print(f"✓ Condiciones: {len(indice.condiciones_por_archivo)}")
    print(f"✓ Referencias en refs.bib: {len(indice.referencias)}")
    print(f"✓ Escrito: {build_dir / 'libro.tex'}")
    print(f"✓ Escrito: {build_dir / 'refs.bib'}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ErrorGeneracion as exc:
        print(f"ERROR LIBRO: {exc}", file=sys.stderr)
        raise SystemExit(1)
