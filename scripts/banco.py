#!/usr/bin/env python3
"""Carga el índice y extrae sus datos. Aquí no se tipografía ninguna salida.

Es el suelo común de `qmd.py`, `libro.py`, `epub.py` y
`verificar_publicacion.py`. Antes este código vivía dentro de `libro.py` y
`epub.py` lo importaba como «motor», de modo que el generador de LaTeX era a la
vez la biblioteca de todos: bastaba tocar una función de datos para mover el
libro impreso sin querer. Ahora los datos están aquí y los renderizadores no
saben nada unos de otros.

Lo que este módulo garantiza:

  · Un `ref` o un `concepto` que no exista **aborta**. Nunca se tipografía un
    hueco: es la regla dura de CLAUDE.md, repetida aquí porque un cociente sin
    procedencia visible es peor que una compilación fallida.
  · Una arista o una condición con una clave que ningún renderizador conoce
    **aborta**. Si el índice aprende un campo, el renderizador lo aprende en el
    mismo cambio.
  · Una figura sin atribución completa **aborta**. No se omite la imagen ni se
    infiere su crédito.

`scripts/build.py` sigue siendo la única autoridad de validación del índice;
esto no la sustituye ni repite sus reglas enteras.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("Falta PyYAML:  pip install pyyaml")


TITULO = "Índice de Semiótica Clínica"
SUBTITULO = "Conceptos, condiciones y sus cocientes de verosimilitud, verificados"
AUTOR = "Dr. Alcy Edmundo Torres Guerrero"
EDITORIAL = "Power Semiotics"

# Dominio donde medsemiotics publica el artículo de cada condición. El índice
# no publica: solo enlaza. Ver «La asimetría con holonmed» en CLAUDE.md.
DOMINIO_PUBLICO = "https://powersemiotics.com/medsemiotics/"

AVISO = (
    "Índice de hechos clínicos verificados: umbrales, códigos y cocientes de "
    "verosimilitud con su fuente. No es material didáctico ni sustituye el "
    "juicio clínico — ver medsemiotics y biosemiotics para la exposición "
    "educativa de este mismo contenido."
)

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


class ErrorGeneracion(RuntimeError):
    pass


# ── Metadatos de citación ─────────────────────────────────────────────────


class Citacion:
    """DOI, ORCID, versión y materias, leídos de `CITATION.cff`.

    No se copian a mano en el generador: el archivo es YAML versionado y ya es
    la autoridad para GitHub y para Zenodo. Duplicar el DOI en un `.py` es
    exactamente cómo el contenedor EPUB acaba declarando una versión que ya no
    existe.
    """

    def __init__(self, raiz: Path):
        ruta = raiz / "CITATION.cff"
        if not ruta.is_file():
            raise ErrorGeneracion("falta CITATION.cff: sin él no hay DOI ni licencia")
        datos = yaml.safe_load(ruta.read_text(encoding="utf-8")) or {}
        self.doi = str(datos.get("doi") or "")
        if not self.doi:
            raise ErrorGeneracion("CITATION.cff no declara «doi»")
        self.doi_url = f"https://doi.org/{self.doi}"
        self.version = str(datos.get("version") or "")
        self.licencia = str(datos.get("license") or "")
        self.materias = [str(k) for k in (datos.get("keywords") or [])]
        autores = datos.get("authors") or []
        orcid = str((autores[0] if autores else {}).get("orcid") or "")
        # El CFF guarda el ORCID como URL; el OPF y Quarto quieren el número.
        self.orcid = orcid.rsplit("/", 1)[-1]

    @property
    def licencia_larga(self) -> str:
        return f"{self.licencia} — {self.licencia_url}"

    @property
    def licencia_url(self) -> str:
        if self.licencia.upper().startswith("CC0"):
            return "https://creativecommons.org/publicdomain/zero/1.0/"
        raise ErrorGeneracion(
            f"licencia «{self.licencia}» sin URL conocida: añádela a banco.py "
            "en el mismo cambio que la introduce en CITATION.cff"
        )


def version_git(raiz: Path) -> str:
    try:
        return subprocess.run(
            ["git", "describe", "--always", "--dirty"],
            cwd=raiz, check=True, capture_output=True, text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "sin-versión-git"


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

    def _cargar(self, directorio: str) -> dict:
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

    def condiciones_de_clase(self, clase: str) -> list:
        grupo = [
            (archivo, c)
            for archivo, c in self.condiciones_por_archivo.items()
            if c.get("clase") == clase
        ]
        return sorted(grupo, key=lambda kv: kv[1].get("termino", ""))


def resolver_ref(indice: Indice, ref_id, donde: str) -> str:
    """La clave BibTeX de una referencia, o aborta: no hay cita a un registro
    que no existe. Es la misma regla dura que build.py, repetida aquí porque
    tipografiar un hueco en vez de fallar sería peor que fallar."""
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


def imagenes_de_registro(indice: Indice, registro: dict, donde: str) -> list:
    """Todas las imágenes de un concepto o condición, con atribución y archivo."""
    imagenes = []
    for i, medio in enumerate(registro.get("medios") or [], 1):
        if medio.get("tipo") != "imagen":
            continue
        faltantes = [c for c in REQUERIDOS_IMAGEN if not medio.get(c)]
        if faltantes:
            raise ErrorGeneracion(f"{donde}: medio {i} sin {', '.join(faltantes)}")
        ruta = (indice.raiz / medio["archivo_local"]).resolve()
        try:
            ruta.relative_to(indice.raiz.resolve())
        except ValueError:
            raise ErrorGeneracion(
                f"{donde}: medio {i} apunta fuera del repositorio"
            )
        if not ruta.is_file():
            raise ErrorGeneracion(f"{donde}: no existe {medio['archivo_local']}")
        imagenes.append(medio)
    return imagenes


def figura_en_latex(relativa: Path, fuente: str) -> bool:
    """¿La figura llegó al LaTeX, convertida o no?

    Quarto convierte los SVG a PDF antes de pasárselos a LuaLaTeX —LaTeX no
    incluye SVG— y los deja bajo `index_files/mediabag/`. La ruta declarada en
    `archivo_local` sigue siendo la autoridad, pero se acepta su equivalente
    convertido: exigir el `.svg` literal daría por perdida una figura que sí
    está en el libro. La conversión necesita `rsvg-convert` en el PATH; sin él
    Quarto aborta el PDF en vez de omitir la imagen.
    """
    candidatos = [relativa.as_posix()]
    if relativa.suffix.lower() == ".svg":
        candidatos += [
            relativa.with_suffix(".pdf").as_posix(),
            relativa.with_suffix(".png").as_posix(),
        ]
    return any(c in fuente for c in candidatos)


# ── BibTeX ────────────────────────────────────────────────────────────────
#
# `refs.bib` ya no alimenta a biblatex —el libro emite su bibliografía resuelta,
# ver `referencia_casa()`—, pero se sigue derivando y viajando dentro del
# paquete LaTeX: es el archivo que citan hoy las fichas de biosemiotics por su
# `clave_bibtex`, y sin él la migración no puede resolver `refs: [lichtenstein2008]`.

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
        lineas.append(f"  {k} = {{{escape_latex(v)}}}{coma}")
    lineas.append("}")
    return "\n".join(lineas)


def build_bibtex(indice: Indice) -> str:
    entradas = [
        entrada_bibtex(ref)
        for _, ref in sorted(
            indice.referencias.items(), key=lambda kv: kv[1].get("clave_bibtex", "")
        )
    ]
    return "\n\n".join(entradas) + "\n"


# ── Citas resueltas ───────────────────────────────────────────────────────
#
# El libro NO delega en citeproc ni en biblatex. Numera él mismo en orden de
# aparición y emite la referencia con el estilo de la casa —PMID y DOI como
# enlaces—, que es lo que hace verificable un cociente. La ventaja práctica:
# EPUB, PDF y HTML salen del mismo Markdown sin depender de un motor de citas
# distinto por formato, y la columna «Fuente» de la tabla de signos vuelve a
# caber en la página porque lleva `[3]` y no la cita entera.


def md_texto(texto) -> str:
    """Texto plano del índice, seguro dentro de Markdown.

    Se escapa la puntuación que pandoc interpreta. Hay títulos que traen un
    asterisco literal y umbrales que empiezan por `>`: sin escapar, el primero
    abre una cursiva que se cierra donde no debe y el segundo convierte el
    renglón en una cita en bloque.
    """
    if texto is None:
        return ""
    salida = []
    for caracter in str(texto):
        if caracter in "\\`*_{}[]<>#|":
            salida.append("\\" + caracter)
        else:
            salida.append(caracter)
    return "".join(salida)


def referencia_casa(ref: dict) -> str:
    """Una entrada de bibliografía: autores, título, revista, PMID y DOI.

    El PMID y el DOI van como enlaces porque son la parte comprobable de la
    cita: quien lee el libro debe poder llegar al registro de PubMed en un
    clic, que es justo lo que este repositorio existe para garantizar.
    """
    autores = [str(a) for a in (ref.get("autores") or [])]
    if len(autores) > 3:
        firma = ", ".join(autores[:3]) + ", et al"
    else:
        firma = ", ".join(autores)

    partes = [p for p in (md_texto(firma), md_texto(ref.get("titulo") or "")) if p]
    revista = md_texto(ref.get("publicacion") or "")
    if revista:
        detalle = f"*{revista}*"
        if ref.get("anio"):
            detalle += f". {ref['anio']}"
        if ref.get("volumen"):
            detalle += f";{ref['volumen']}"
        if ref.get("paginas"):
            detalle += f":{ref['paginas']}"
        partes.append(detalle)

    identificadores = ref.get("identificadores") or {}
    if identificadores.get("pmid"):
        pmid = identificadores["pmid"]
        partes.append(f"PMID [{pmid}](https://pubmed.ncbi.nlm.nih.gov/{pmid}/)")
    if identificadores.get("doi"):
        doi = identificadores["doi"]
        partes.append(f"doi:[{doi}](https://doi.org/{doi})")

    # Una retractación no se calla: es la razón por la que PubMed manda sobre
    # CrossRef en este repositorio.
    if (ref.get("verificacion") or {}).get("retractado"):
        partes.append("**RETRACTADO**")

    return ". ".join(p.rstrip(".") for p in partes if p) + "."


class Citas:
    """Numera las referencias del libro en orden de aparición.

    Un mismo `ref` citado en dos condiciones conserva su número: el lector que
    vuelve a ver `[7]` sabe que es la misma fuente. Cada condición cierra
    listando las suyas, y el libro cierra con todas.
    """

    def __init__(self, indice: Indice):
        self.indice = indice
        self.orden: list = []
        self.locales: list = []

    def abrir_capitulo(self) -> None:
        self.locales = []

    def marca(self, ref_id, donde: str) -> str:
        """`[n]` para la referencia, validándola de paso. Aborta si no existe."""
        resolver_ref(self.indice, ref_id, donde)
        clave = str(ref_id)
        if clave not in self.orden:
            self.orden.append(clave)
        if clave not in self.locales:
            self.locales.append(clave)
        return f"[{self.orden.index(clave) + 1}]"

    def numero(self, ref_id) -> int:
        return self.orden.index(str(ref_id)) + 1

    def lista(self, claves: list) -> list:
        """Las referencias dadas, numeradas con su número global."""
        return [
            linea
            for c in claves
            for linea in (
                f"\\[{self.numero(c)}\\] {referencia_casa(self.indice.referencia(c))}", ""
            )
        ]

    def sin_citar(self) -> list:
        """Los registros del índice que ningún capítulo cita todavía.

        El libro anterior imprimía las 100 referencias en su bibliografía sin
        distinguir cuáles usaba. Numerar en orden de aparición dejaría fuera a
        las que aún no cita ninguna condición —la mayoría, porque llegaron con
        el `refs.bib` de biosemiotics y se citan desde allí—, y perder 80
        registros verificados no es una mejora de maquetación. Se listan
        aparte, dichas por lo que son.
        """
        return sorted(
            (c for c in self.indice.referencias if c not in self.orden),
            key=lambda c: self.indice.referencia(c).get("clave_bibtex", ""),
        )


# ── Aristas (signos) ──────────────────────────────────────────────────────
#
# Claves conocidas dentro de una arista (`signos`/`signos_de_alarma`) y de sus
# bloques anidados. Un campo que aparezca aquí y no se maneje en
# `filas_de_signo` sería peor que un error: se leería como si el generador lo
# hubiera considerado. Relevadas con un barrido real de las condiciones, no de
# memoria.

CLAVES_ARISTA_CONOCIDAS = {
    "concepto", "rol", "estado_lr", "lr_positivo", "lr_negativo",
    "motivo", "decision", "nota", "advertencia", "ref", "poblacion",
    "sensibilidad", "especificidad", "ic95_sensibilidad", "ic95_especificidad",
    "efecto", "dispara_si", "sostiene", "odds_ratio",
    "tramos", "sensibilidad_por_diametro", "sensibilidad_por_gravedad",
}
CLAVES_LR_CONOCIDAS = {
    "valor", "rango", "ic95", "ref", "nota", "umbral_condicion", "umbral",
    "poblacion",
}
CLAVES_TRAMO_CONOCIDAS = {
    "umbral_condicion", "umbral", "lr_positivo", "ic95", "lr_negativo",
    "ic95_negativo", "ref", "especificidad", "sensibilidad",
}

# Claves del `balance` que NO son un nivel de certeza. Lista blanca a propósito,
# igual que en build.py: descartar lo que no parezca nivel convertiría en grado
# de certeza cualquier clave nueva que lleve un diccionario.
BALANCE_META = ("ref", "nota", "fuente")

CAMPOS_CONOCIDOS = {
    "id", "tipo", "clase", "termino", "termino_en", "sinonimos", "codigos",
    "probabilidad_base", "factores_riesgo", "signos", "procedencia",
    "conclusion_de_la_fuente", "pendiente", "reglas", "escalas",
    "signos_de_alarma", "nucleo", "balance",
    # Declarativamente honestos, pero no clínicos: se tipografían igual con el
    # renderizador genérico para no perderlos.
    "no_emitidos", "discrepancias", "modificadores", "notas_de_uso",
    "url", "medios",
}


def numero(v) -> str:
    return f"{v:g}" if isinstance(v, (int, float)) else str(v)


def porcentaje(v, etiqueta: str) -> str:
    """`Se 87%` cuando el índice guarda 0.87; tal cual cuando ya viene en texto."""
    if isinstance(v, float) and v <= 1:
        return f"{etiqueta} {v:.0%}"
    return f"{etiqueta} {v}"


def _lr_texto(lr: dict, etiqueta: str) -> str:
    """Cociente + IC95 + umbral, en texto plano sin escapar todavía."""
    if lr.get("valor") is not None:
        texto = f"{etiqueta} {numero(lr['valor'])}"
    elif lr.get("rango"):
        texto = f"{etiqueta} " + "–".join(numero(v) for v in lr["rango"])
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

    def __init__(self, etiqueta: str, rol: str, cociente: str, citas: list):
        self.etiqueta = etiqueta
        self.rol = rol
        self.cociente = cociente
        self.citas = citas


def filas_de_signo(indice: Indice, arista: dict, donde: str):
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
            f"{donde} ({termino}): clave(s) {', '.join(sobrantes)} sin "
            "renderizador en banco.py"
        )

    filas: list = []
    tramos = arista.get("tramos")
    if tramos:
        for tramo in tramos:
            sobrantes_t = sorted(set(tramo) - CLAVES_TRAMO_CONOCIDAS)
            if sobrantes_t:
                raise ErrorGeneracion(
                    f"{donde} ({termino}), tramo: clave(s) "
                    f"{', '.join(sobrantes_t)} sin renderizador"
                )
            piezas = []
            if tramo.get("lr_positivo") is not None:
                texto = f"LR+ {numero(tramo['lr_positivo'])}"
                if tramo.get("ic95"):
                    texto += f" (IC95% {tramo['ic95'][0]}–{tramo['ic95'][1]})"
                piezas.append(texto)
            if tramo.get("lr_negativo") is not None:
                texto = f"LR- {numero(tramo['lr_negativo'])}"
                if tramo.get("ic95_negativo"):
                    texto += (
                        f" (IC95% {tramo['ic95_negativo'][0]}–"
                        f"{tramo['ic95_negativo'][1]})"
                    )
                piezas.append(texto)
            if tramo.get("especificidad") is not None:
                piezas.append(porcentaje(tramo["especificidad"], "Sp"))
            if tramo.get("sensibilidad") is not None:
                piezas.append(porcentaje(tramo["sensibilidad"], "Se"))
            citas = []
            if tramo.get("ref"):
                resolver_ref(indice, tramo["ref"], f"{donde} ({termino}, tramo)")
                citas.append(str(tramo["ref"]))
            umbral = tramo.get("umbral_condicion") or tramo.get("umbral") or "?"
            filas.append(
                FilaSigno(f"{termino} ({umbral})", rol, " / ".join(piezas), citas)
            )
    elif estado in ("no_medible", "no_medido"):
        citas = []
        if arista.get("ref"):
            resolver_ref(indice, arista["ref"], donde)
            citas.append(str(arista["ref"]))
        filas.append(
            FilaSigno(
                termino, rol,
                "no medible" if estado == "no_medible" else "no medido",
                citas,
            )
        )
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
                    f"{donde} ({termino}), {campo}: clave(s) "
                    f"{', '.join(sobrantes_lr)} sin renderizador"
                )
            texto = _lr_texto(bloque, etiqueta_lr)
            if texto:
                piezas.append(texto)
            if bloque.get("ref"):
                resolver_ref(indice, bloque["ref"], f"{donde} ({termino})")
                if str(bloque["ref"]) not in citas:
                    citas.append(str(bloque["ref"]))
        if arista.get("ref"):
            resolver_ref(indice, arista["ref"], donde)
            if str(arista["ref"]) not in citas:
                citas.append(str(arista["ref"]))
        cociente = " / ".join(piezas) if piezas else (estado or "—")
        filas.append(FilaSigno(termino, rol, cociente, citas))

    notas: list = []
    for campo, etiqueta in (("lr_positivo", "LR+"), ("lr_negativo", "LR-")):
        bloque = arista.get(campo) or {}
        for atributo in ("nota", "poblacion"):
            if bloque.get(atributo):
                notas.append((f"{termino} — {etiqueta} {atributo}", frase(bloque[atributo])))
    for etiqueta, campo in (
        ("Decisión", "decision"), ("Advertencia", "advertencia"),
        ("Motivo", "motivo"), ("Nota", "nota"),
    ):
        if arista.get(campo):
            notas.append((f"{termino} — {etiqueta}", frase(arista[campo])))

    if arista.get("poblacion"):
        notas.append((f"{termino} — Población", frase(arista["poblacion"])))

    # `efecto`, `dispara_si` y `sostiene` son lo que holonmed lee para decidir
    # si una arista dispara una bandera roja y con qué autoridad. Estaban en la
    # lista blanca sin renderizador, así que el libro los perdía en silencio
    # justo en las condiciones donde más pesan.
    if arista.get("efecto") or arista.get("dispara_si") or arista.get("sostiene"):
        piezas_efecto = []
        if arista.get("efecto"):
            piezas_efecto.append(str(arista["efecto"]).replace("_", " "))
        if arista.get("dispara_si"):
            piezas_efecto.append(f"si el hallazgo está {arista['dispara_si']}")
        texto = ", ".join(piezas_efecto)
        if arista.get("sostiene"):
            sostiene = str(arista["sostiene"]).replace("_", " ")
            texto = f"{texto}; sostenido por {sostiene}" if texto else sostiene
        notas.append((f"{termino} — Efecto", frase(texto)))

    if arista.get("odds_ratio") is not None:
        bruto = arista["odds_ratio"]
        if isinstance(bruto, dict):
            sobrantes_or = sorted(set(bruto) - (CLAVES_LR_CONOCIDAS | {"covariables"}))
            if sobrantes_or:
                raise ErrorGeneracion(
                    f"{donde} ({termino}), odds_ratio: clave(s) "
                    f"{', '.join(sobrantes_or)} sin renderizador"
                )
            texto = _lr_texto(bruto, "OR")
            for campo in ("covariables", "poblacion", "nota"):
                if bruto.get(campo):
                    texto += f"; {campo}: {bruto[campo]}"
            if bruto.get("ref"):
                resolver_ref(indice, bruto["ref"], f"{donde} ({termino}, OR)")
                # La cita viaja en la fila, no en la nota: la columna «Fuente»
                # es donde el lector busca la procedencia de un número.
                if filas and str(bruto["ref"]) not in filas[0].citas:
                    filas[0].citas.append(str(bruto["ref"]))
        else:
            texto = f"OR {numero(bruto)}"
        if texto:
            notas.append((f"{termino} — Odds ratio", texto + "."))

    rendimiento = []
    if arista.get("sensibilidad") is not None:
        texto = porcentaje(arista["sensibilidad"], "Se")
        if arista.get("ic95_sensibilidad"):
            texto += (
                f" (IC95% {arista['ic95_sensibilidad'][0]}–"
                f"{arista['ic95_sensibilidad'][1]})"
            )
        rendimiento.append(texto)
    if arista.get("especificidad") is not None:
        texto = porcentaje(arista["especificidad"], "Sp")
        if arista.get("ic95_especificidad"):
            texto += (
                f" (IC95% {arista['ic95_especificidad'][0]}–"
                f"{arista['ic95_especificidad'][1]})"
            )
        rendimiento.append(texto)
    if rendimiento:
        notas.append((f"{termino} — Rendimiento", ", ".join(rendimiento) + "."))

    for campo, etiqueta_campo in (
        ("sensibilidad_por_diametro", "Sensibilidad por diámetro"),
        ("sensibilidad_por_gravedad", "Sensibilidad por gravedad"),
    ):
        tramos_sens = arista.get(campo)
        if tramos_sens:
            clave_tramo = (
                "diametro" if campo == "sensibilidad_por_diametro" else "gravedad"
            )
            piezas = [
                f"{t.get(clave_tramo, '?')}: {t.get('sensibilidad')}"
                for t in tramos_sens
            ]
            notas.append((f"{termino} — {etiqueta_campo}", "; ".join(piezas) + "."))

    return filas, notas
