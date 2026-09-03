#!/usr/bin/env python3
"""Proyecta el índice a un proyecto Quarto book (`build/quarto/`).

    python scripts/qmd.py [--destino build/quarto]

El índice YAML de `conceptos/`, `condiciones/` y `referencias/` sigue siendo la
única fuente de verdad; este script NO lo modifica. Lo que produce es un
proyecto Quarto derivado y desechable, del que salen EPUB, PDF y HTML con un
solo `quarto render`.

Sustituye a dos renderizadores paralelos del mismo contenido: las ~900 líneas
de LaTeX a mano de `libro.py` (escape, longtable, figuras, preámbulo) y el
ensamblado Markdown propio de `epub.py`. Mantenerlos sincronizados era trabajo
manual, y ya habían divergido: la edición EPUB no tipografiaba `nucleo` ni
`balance`, así que el núcleo diagnóstico de las condiciones que lo declaran
—Parkinson entre ellas— no aparecía en el libro electrónico y nadie lo notó.

Tres decisiones que no son de estilo:

1.  **Jerarquía.** `#` parte (Vocabulario, Enfermedades, Síndromes) → `##`
    grupo del vocabulario o condición → bloques en negrita dentro de la
    condición. Los bloques NO son encabezados: con `toc-depth: 2` el índice
    lista partes y condiciones, que es como se busca una condición, y no
    catorce «Signos.» repetidos.
2.  **Citas.** NO se delega en citeproc ni en biblatex. Se numera en orden de
    aparición y se emite la referencia con el estilo de la casa —PMID y DOI
    como enlaces—, igual en los tres formatos. La columna «Fuente» de la tabla
    de signos vuelve a caber en la página porque lleva `[3]` y no la cita
    entera, y cada condición cierra con sus propias fuentes.
3.  **Imágenes.** Se copian dentro del proyecto conservando su `archivo_local`
    en vez de referenciarse con `../assets/...`. Así el directorio generado es
    autocontenido —se empaqueta o se mueve sin arrastrar el checkout— y
    `verificar_publicacion.py` puede comparar la ruta declarada tal cual.

El contrato de figuras se mantiene sin excepción: a una figura le faltan datos
de atribución y la generación aborta. No se omite la imagen ni se infiere su
crédito.
"""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import unicodedata
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import banco  # noqa: E402  (import tras ajustar sys.path)
from banco import ErrorGeneracion, frase, md_texto  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def slug(texto: str) -> str:
    """Nombre de archivo estable y ASCII para un capítulo generado."""
    plano = unicodedata.normalize("NFKD", str(texto))
    plano = plano.encode("ascii", "ignore").decode("ascii").lower()
    plano = re.sub(r"[^a-z0-9]+", "-", plano).strip("-")
    return plano or "seccion"


def celda(texto) -> str:
    """Una celda de tabla: sin saltos de línea y con la puntuación escapada."""
    return " ".join(md_texto(texto).split())


# ── Vocabulario ───────────────────────────────────────────────────────────


def dato_markdown(valor, citas: banco.Citas, donde: str) -> str:
    """Datos estructurados, conservando sus claves y resolviendo cada ref."""
    if isinstance(valor, dict):
        partes = []
        for clave, dato in valor.items():
            if dato is None or dato == [] or dato == {}:
                continue
            if clave == "ref":
                partes.append(citas.marca(dato, donde))
            else:
                etiqueta = {"lr_positivo": "LR+", "lr_negativo": "LR−",
                            "lr_positivo_rango": "LR+ (rango)", "lr_negativo_rango": "LR− (rango)",
                            "ic95": "IC95%"}.get(clave, clave.replace("_", " "))
                partes.append(f"{md_texto(etiqueta)}: {dato_markdown(dato, citas, donde)}")
        return "; ".join(partes)
    if isinstance(valor, list):
        return " / ".join(dato_markdown(dato, citas, donde) for dato in valor)
    return md_texto(valor)


def entrada_concepto_md(cid: str, concepto: dict, citas: banco.Citas) -> list:
    """Un término del vocabulario como entrada de lista de definiciones.

    La definición arranca SIEMPRE por el código `HM:`, que es permanente y es
    lo que citan holonmed, biosemiotics y medsemiotics. El libro anterior lo
    omitía: publicaba el vocabulario sin las claves con las que se lo consulta.
    """
    detalle = [f"`{cid}`"]
    conocidos = {
        "id", "tipo", "termino", "termino_en", "semantica", "padre", "sinonimos",
        "codigos", "umbral", "significante", "significado", "falsos_positivos",
        "componentes", "contrasta_con", "se_basa_en", "procedencia", "medios",
    }
    sobrantes = set(concepto) - conocidos
    if sobrantes:
        raise ErrorGeneracion(f"{cid}: campos sin renderizador: {', '.join(sorted(sobrantes))}")
    if concepto.get("sinonimos"):
        detalle.append("sinónimos: " + md_texto(", ".join(concepto["sinonimos"])))
    codigos = [(k, v) for k, v in (concepto.get("codigos") or {}).items() if v]
    if codigos:
        detalle.append("códigos: " + md_texto(", ".join(f"{k} {v}" for k, v in codigos)))
    umbral = concepto.get("umbral")
    if umbral:
        detalle.append("umbral: " + dato_markdown(umbral, citas, cid))
    for campo in ("termino_en", "semantica", "padre", "significante", "significado",
                  "componentes", "falsos_positivos", "contrasta_con", "se_basa_en"):
        if concepto.get(campo):
            detalle.append(md_texto(campo.replace("_", " ")) + ": " + dato_markdown(concepto[campo], citas, cid))
    return [
        md_texto(concepto.get("termino") or cid),
        ":   " + " · ".join(detalle),
        "",
    ]


def capitulo_vocabulario(indice: banco.Indice, figuras: list, citas: banco.Citas) -> str:
    lineas = ["# Vocabulario", ""]
    ubicados: set = set()
    ilustrados_en_condiciones = {
        str(signo.get("concepto"))
        for condicion in indice.condiciones_por_archivo.values()
        for signo in condicion.get("signos") or []
    }

    def entrada(cid: str) -> list:
        concepto = indice.concepto(cid)
        salida = entrada_concepto_md(cid, concepto, citas)
        if cid not in ilustrados_en_condiciones:
            salida += figuras_de_registro(indice, concepto, cid, figuras)
        return salida

    for raiz_id, titulo in banco.GRUPOS_VOCABULARIO:
        hijos = sorted(
            (
                cid for cid, c in indice.conceptos.items()
                if c.get("padre") == raiz_id and cid != raiz_id
            ),
            key=lambda cid: indice.termino(cid),
        )
        if not hijos and raiz_id not in indice.conceptos:
            continue
        lineas += [f"## {md_texto(titulo)}", ""]
        if raiz_id in indice.conceptos:
            ubicados.add(raiz_id)
            lineas += entrada(raiz_id)
        if not hijos:
            lineas += ["*Sin conceptos hijos todavía.*", ""]
            continue
        for cid in hijos:
            ubicados.add(cid)
            lineas += entrada(cid)

    huerfanos = sorted(
        (cid for cid in indice.conceptos if cid not in ubicados),
        key=lambda cid: indice.termino(cid),
    )
    if huerfanos:
        lineas += [
            "## Otros conceptos",
            "",
            "*Conceptos cuyo padre no está en los grupos de arriba: "
            "probablemente una condición del vocabulario semilla o un nivel "
            "intermedio nuevo.*",
            "",
        ]
        for cid in huerfanos:
            lineas += entrada(cid)

    return "\n".join(lineas).rstrip() + "\n"


# ── Figuras ───────────────────────────────────────────────────────────────


def figura_markdown(medio: dict) -> str:
    """Figura con su pie completo de atribución, en ruta interna al proyecto.

    El pie lleva fuente y licencia como ENLACES. Es la condición de la licencia
    de la imagen, no una preferencia editorial: por eso se lee con `markdown`
    y no con `gfm`, que acepta `implicit_figures` pero la ignora y aplana el
    pie a un `alt=` de texto plano.
    """
    pie = (
        f"{md_texto(' '.join(medio['descripcion'].split()))}. {md_texto(' '.join(medio['credito'].split()))}. "
        f"[{md_texto(medio['fuente'])}]({medio['fuente_url']}). "
        f"[{md_texto(medio['licencia_img'])}]({medio['licencia_url']})."
    )
    # El ancho es un tope, no una preferencia: sin él Quarto compone cada
    # imagen a su tamaño natural y una figura de página entera empuja el texto
    # que la explica a la página siguiente. El generador LaTeX anterior lo
    # limitaba con `max width=0.85\textwidth`; aquí se declara una vez, en el
    # Markdown, y lo respetan los tres formatos.
    return f"![{pie}]({medio['archivo_local']}){{width=80%}}"


def figuras_de_registro(indice: banco.Indice, registro: dict, donde: str, recogidas: list) -> list:
    lineas = []
    for medio in banco.imagenes_de_registro(indice, registro, donde):
        recogidas.append((registro, medio))
        lineas += [figura_markdown(medio), ""]
    return lineas


def figuras_de_condicion(
    indice: banco.Indice, signos: list, donde: str, recogidas: list
) -> list:
    """Todas las figuras de cada concepto, sin repetir aristas de la condición."""
    lineas: list = []
    vistos: set = set()
    for arista in signos:
        cid = str(arista.get("concepto") or "")
        if not cid or cid in vistos:
            continue
        concepto = banco.resolver_concepto(indice, cid, donde)
        vistos.add(cid)
        lineas += figuras_de_registro(indice, concepto, f"{donde} ({concepto.get('termino')})", recogidas)
    return lineas


# ── Condiciones ───────────────────────────────────────────────────────────


def tabla_signos(
    indice: banco.Indice, signos: list, donde: str, citas: banco.Citas
) -> list:
    """La tabla de signos y sus notas al pie.

    Los anchos relativos salen del número de guiones del separador: el cociente
    con su IC95 y su umbral es la columna larga, y la fuente ya no es la cita
    entera sino su número.
    """
    lineas = [
        "| Hallazgo | Rol | Cociente | Fuente |",
        "|" + "-" * 28 + "|" + "-" * 12 + "|" + "-" * 40 + "|" + "-" * 8 + "|",
    ]
    notas_todas: list = []
    for arista in signos:
        filas, notas = banco.filas_de_signo(indice, arista, donde)
        for fila in filas:
            marcas = " ".join(citas.marca(c, donde) for c in fila.citas)
            lineas.append(
                f"| {celda(fila.etiqueta)} | {celda(fila.rol)} | "
                f"{celda(fila.cociente)} | {marcas} |"
            )
        notas_todas += notas
    lineas.append("")
    for etiqueta, texto in notas_todas:
        lineas.append(f"- **{md_texto(etiqueta)}.** {md_texto(texto)}")
    if notas_todas:
        lineas.append("")
    return lineas


def bloque_probabilidad_base(
    indice: banco.Indice, condicion: dict, donde: str, citas: banco.Citas
) -> list:
    base = condicion.get("probabilidad_base")
    if base is None:
        return []
    if not isinstance(base, dict):
        return [f"**Probabilidad base.** {md_texto(base)}.", ""]

    partes = []
    if base.get("valor") is not None:
        valor = base["valor"]
        texto = (
            f"{valor:.0%}" if isinstance(valor, float) and valor <= 1 else str(valor)
        )
        partes.append(md_texto(texto))
    elif base.get("rango"):
        partes.append(md_texto("–".join(str(v) for v in base["rango"])))
    linea = "**Probabilidad base.**"
    if partes:
        linea += " " + partes[0] + "."
    if base.get("poblacion"):
        linea += " " + md_texto(frase(f"Población: {base['poblacion']}"))
    if base.get("ref"):
        linea += " " + citas.marca(base["ref"], f"{donde} (probabilidad base)")
    return [linea, ""]


def bloque_factores_riesgo(condicion: dict) -> list:
    factores = condicion.get("factores_riesgo") or []
    if not factores:
        return []
    lineas = ["**Factores de riesgo.**", ""]
    for factor in factores:
        if isinstance(factor, dict):
            nombre = (
                factor.get("nombre") or factor.get("factor")
                or factor.get("termino") or ""
            )
        else:
            nombre = factor
        lineas.append(f"- {md_texto(frase(nombre))}")
    lineas.append("")
    return lineas


def bloque_nucleo_balance(
    indice: banco.Indice, condicion: dict, donde: str, citas: banco.Citas
) -> list:
    """Núcleo y balance diagnósticos.

    Este bloque NO existía en la edición EPUB: solo lo tipografiaba el
    generador LaTeX. Es el criterio con el que la condición se define, así que
    su ausencia no era un detalle de maquetación.
    """
    lineas: list = []

    nucleo = condicion.get("nucleo")
    if isinstance(nucleo, dict):
        partes = []
        for campo, etiqueta in (
            ("requiere", "requiere"),
            ("y_al_menos_uno_de", "y al menos uno de"),
        ):
            terminos = [banco.resolver_concepto(indice, str(c), donde)['termino'] for c in (nucleo.get(campo) or [])]
            if terminos:
                partes.append(f"{etiqueta}: " + ", ".join(terminos))
        linea = "**Núcleo diagnóstico.** " + md_texto("; ".join(partes)) + "."
        if nucleo.get("ref"):
            linea += " " + citas.marca(nucleo["ref"], f"{donde} (núcleo)")
        lineas += [linea, ""]
        extras = {k: v for k, v in nucleo.items() if k not in ("ref", "requiere", "y_al_menos_uno_de")}
        if extras:
            lineas += [dato_markdown(extras, citas, donde), ""]

    balance = condicion.get("balance")
    if isinstance(balance, dict):
        cabecera = "**Balance diagnóstico.**"
        if balance.get("ref"):
            cabecera += " " + citas.marca(balance["ref"], f"{donde} (balance)")
        lineas += [cabecera, ""]
        for campo in ("nota", "fuente"):
            if balance.get(campo):
                lineas += [dato_markdown({campo: balance[campo]}, citas, donde), ""]
        for nombre, regla in balance.items():
            if nombre in banco.BALANCE_META or not isinstance(regla, dict):
                continue
            campos = ", ".join(f"{k}: {v}" for k, v in regla.items())
            lineas.append(f"- **{md_texto(nombre)}**: {md_texto(campos)}")
        lineas.append("")

    return lineas


def bloque_signos_de_alarma(
    indice: banco.Indice, condicion: dict, donde: str, citas: banco.Citas
) -> list:
    alarmas = condicion.get("signos_de_alarma") or []
    if not alarmas:
        return []
    lineas = ["**Signos de alarma.**", ""]
    for arista in alarmas:
        concepto = banco.resolver_concepto(
            indice, arista.get("concepto"), f"{donde} (signo de alarma)"
        )
        texto = md_texto(concepto.get("termino"))
        if arista.get("nota"):
            texto += ": " + md_texto(frase(arista["nota"]))
        if arista.get("ref"):
            texto += " " + citas.marca(arista["ref"], f"{donde} (signo de alarma)")
        lineas.append(f"- {texto}")
    lineas.append("")
    return lineas


def bloque_reglas(
    indice: banco.Indice, condicion: dict, donde: str, citas: banco.Citas
) -> list:
    reglas = condicion.get("reglas") or []
    if not reglas:
        return []
    lineas = ["**Reglas de clasificación.**", ""]
    for regla in reglas:
        componentes = [indice.termino(str(c)) for c in (regla.get("componentes") or [])]
        texto = md_texto(f"{regla.get('nombre', '')}: {', '.join(componentes)}.")
        for campo in ("criterio", "decision"):
            if regla.get(campo):
                texto += " " + md_texto(frase(regla[campo]))
        if regla.get("ref"):
            texto += " " + citas.marca(regla["ref"], f"{donde} (regla)")
        lineas.append(f"- {texto}")
    lineas.append("")
    return lineas


def bloque_escalas(condicion: dict, citas: banco.Citas, donde: str) -> list:
    escalas = condicion.get("escalas") or []
    lineas: list = []
    for escala in escalas:
        lineas += [f"**Escala: {md_texto(escala.get('nombre', ''))}.**", ""]
        metadatos = {k: v for k, v in escala.items() if k not in ("nombre", "tramos")}
        if metadatos:
            lineas += [dato_markdown(metadatos, citas, donde), ""]
        for tramo in escala.get("tramos") or []:
            lineas.append("- " + dato_markdown(tramo, citas, donde))
        lineas.append("")
    return lineas


def bloque_discrepancias(
    indice: banco.Indice, condicion: dict, donde: str, citas: banco.Citas
) -> list:
    items = condicion.get("discrepancias") or []
    if not items:
        return []
    lineas = ["**Discrepancias entre fuentes.**", ""]
    for item in items:
        concepto = banco.resolver_concepto(
            indice, item.get("concepto"), f"{donde} (discrepancia)"
        )
        lineas += [f"*{md_texto(concepto.get('termino'))}.*", ""]
        if item.get("resumen"):
            lineas += [md_texto(frase(item["resumen"])), ""]
        for etiqueta, campo in (("A favor", "a_favor"), ("En contra", "en_contra")):
            lado = item.get(campo) or {}
            if not lado.get("dice"):
                continue
            texto = f"- **{etiqueta}:** {md_texto(frase(lado['dice']))}"
            if lado.get("ref"):
                texto += " " + citas.marca(
                    lado["ref"], f"{donde} (discrepancia, {etiqueta})"
                )
            lineas.append(texto)
        lineas.append("")
        if item.get("decision"):
            lineas += [md_texto(frase(item["decision"])), ""]
        if item.get("para_reabrirla"):
            lineas += [
                f"*Para reabrirla: {md_texto(frase(item['para_reabrirla']))}*", "",
            ]
    return lineas


def bloque_no_emitidos(indice: banco.Indice, condicion: dict, donde: str) -> list:
    items = condicion.get("no_emitidos") or []
    if not items:
        return []
    lineas = ["**Hallazgos no emitidos, y por qué.**", ""]
    for item in items:
        concepto = banco.resolver_concepto(
            indice, item.get("concepto"), f"{donde} (no emitido)"
        )
        texto = md_texto(frase(item.get("motivo", "")))
        if item.get("nota"):
            texto += " " + md_texto(frase(item["nota"]))
        lineas.append(f"- **{md_texto(concepto.get('termino'))}.** {texto}")
    lineas.append("")
    return lineas


def bloque_modificadores(
    indice: banco.Indice, condicion: dict, donde: str, citas: banco.Citas
) -> list:
    items = condicion.get("modificadores") or []
    if not items:
        return []
    lineas = ["**Modificadores.**", ""]
    for item in items:
        concepto = banco.resolver_concepto(
            indice, item.get("concepto"), f"{donde} (modificador)"
        )
        texto = md_texto(frase(item.get("efecto", "")))
        if item.get("nota"):
            texto += " " + md_texto(frase(item["nota"]))
        if item.get("ref"):
            texto += " " + citas.marca(item["ref"], f"{donde} (modificador)")
        lineas.append(f"- **{md_texto(concepto.get('termino'))}.** {texto}")
    lineas.append("")
    return lineas


def bloque_notas_de_uso(condicion: dict) -> list:
    notas = condicion.get("notas_de_uso") or []
    if not notas:
        return []
    lineas = ["**Notas de uso.**", ""]
    for nota in notas:
        lineas.append(f"- {md_texto(frase(nota))}")
    lineas.append("")
    return lineas


def capitulo_condicion(
    indice: banco.Indice, archivo: str, condicion: dict,
    citas: banco.Citas, figuras: list,
) -> str:
    termino = condicion.get("termino") or archivo
    donde = f"{archivo} ({termino})"
    identificador = slug(str(condicion.get("id") or archivo))
    citas.abrir_capitulo()

    lineas = [f"## {md_texto(termino)} {{#sec-{identificador}}}", ""]
    lineas += [f"`{condicion.get('id') or archivo}`", ""]
    if any((condicion.get("codigos") or {}).values()):
        lineas += ["**Códigos.** " + dato_markdown(condicion["codigos"], citas, donde), ""]

    if condicion.get("termino_en"):
        lineas += [f"*{md_texto(condicion['termino_en'])}*", ""]
    if condicion.get("sinonimos"):
        lineas += ["Sinónimos: " + md_texto(", ".join(condicion["sinonimos"])) + ".", ""]
    # El índice y la plataforma son la misma obra en dos soportes: la ficha
    # impresa apunta al artículo vivo, que es donde está la exposición
    # didáctica y las correcciones posteriores a esta edición.
    if condicion.get("url"):
        lineas += [f"*Artículo en medsemiotics:* <{condicion['url']}>", ""]
    lineas += figuras_de_registro(indice, condicion, donde, figuras)

    lineas += bloque_probabilidad_base(indice, condicion, donde, citas)
    lineas += bloque_factores_riesgo(condicion)
    lineas += bloque_nucleo_balance(indice, condicion, donde, citas)

    if condicion.get("signos"):
        lineas += ["**Signos.**", ""]
        lineas += tabla_signos(indice, condicion["signos"], donde, citas)
        lineas += figuras_de_condicion(indice, condicion["signos"], donde, figuras)

    lineas += bloque_signos_de_alarma(indice, condicion, donde, citas)
    lineas += bloque_reglas(indice, condicion, donde, citas)
    lineas += bloque_escalas(condicion, citas, donde)
    lineas += bloque_discrepancias(indice, condicion, donde, citas)
    lineas += bloque_no_emitidos(indice, condicion, donde)
    lineas += bloque_modificadores(indice, condicion, donde, citas)
    lineas += bloque_notas_de_uso(condicion)

    if condicion.get("conclusion_de_la_fuente"):
        lineas += [
            "**Conclusión de la fuente.** "
            + md_texto(frase(condicion["conclusion_de_la_fuente"])),
            "",
        ]

    if condicion.get("pendiente"):
        lineas += ["**Fuera de alcance, por ahora.**", ""]
        for item in condicion["pendiente"]:
            lineas.append(f"- {md_texto(frase(item))}")
        lineas.append("")

    sobrantes = sorted(set(condicion) - banco.CAMPOS_CONOCIDOS)
    if sobrantes:
        raise ErrorGeneracion(
            f"{donde}: campo(s) {', '.join(sobrantes)} sin renderizador. "
            "Añádelo a qmd.py en el mismo cambio que lo emite el índice."
        )

    if citas.locales:
        lineas += ["**Fuentes.**", ""]
        lineas += citas.lista(citas.locales)
        lineas.append("")

    return "\n".join(lineas)


def capitulo_clase(
    indice: banco.Indice, clase: str, titulo: str,
    citas: banco.Citas, figuras: list,
) -> str:
    lineas = [f"# {md_texto(titulo)}", ""]
    for archivo, condicion in indice.condiciones_de_clase(clase):
        lineas.append(capitulo_condicion(indice, archivo, condicion, citas, figuras))
    return "\n".join(lineas).rstrip() + "\n"


# ── Preliminares y apéndices ──────────────────────────────────────────────


def portadilla(citacion: banco.Citacion, version: str) -> str:
    return "\n".join([
        "# Portadilla {.unnumbered}",
        "",
        f"**{banco.SUBTITULO}**",
        "",
        f"{banco.AUTOR} · ORCID "
        f"[{citacion.orcid}](https://orcid.org/{citacion.orcid})",
        "",
        f"{banco.EDITORIAL} · Compilación {date.today().isoformat()} · "
        f"versión `{version}`",
        "",
        "## Créditos, licencia y uso {.unnumbered}",
        "",
        f"Autor: {banco.AUTOR}. Editorial: {banco.EDITORIAL}. Idioma: español.",
        "",
        f"Identificador DOI: [{citacion.doi}]({citacion.doi_url}).",
        "",
        f"El índice se distribuye bajo "
        f"[{citacion.licencia}]({citacion.licencia_url}). Las figuras conservan "
        "sus licencias propias, declaradas en cada pie y en los créditos "
        "finales.",
        "",
        f"**Aviso:** {banco.AVISO}",
        "",
        "Este libro no añade prosa al índice: tipografía los hechos que ya "
        "están en el YAML —términos, sinónimos, umbrales, cocientes con su "
        "intervalo y su fuente—. La exposición didáctica de este mismo "
        "contenido vive en medsemiotics y en biosemiotics.",
        "",
    ])


def bibliografia_capitulo(citas: banco.Citas) -> str:
    """Las fuentes citadas, numeradas, y las que el índice trae sin citar aún.

    Los dos bloques están separados a propósito. Mezclarlos —como hacía la
    edición anterior, que listaba las cien referencias sin distinguir— hace
    imposible saber sobre qué se apoya de verdad este libro.
    """
    lineas = ["# Bibliografía {.unnumbered}", ""]
    lineas += citas.lista(citas.orden)
    lineas.append("")

    pendientes = citas.sin_citar()
    if pendientes:
        lineas += [
            "## Otras referencias del índice {.unnumbered}",
            "",
            "*Registros verificados contra PubMed que ningún capítulo de esta "
            "edición cita todavía. Se listan porque forman parte del índice y "
            "otros proyectos del ecosistema los citan por su clave.*",
            "",
        ]
        for clave in pendientes:
            lineas.append(
                f"- {banco.referencia_casa(citas.indice.referencia(clave))}"
            )
        lineas.append("")
    return "\n".join(lineas)


def creditos_imagenes(figuras: list) -> str:
    lineas = ["# Créditos de imágenes {.unnumbered}", ""]
    for concepto, medio in figuras:
        lineas.append(
            f"- **{md_texto(concepto.get('termino'))}:** {md_texto(medio['descripcion'])}. "
            f"{md_texto(medio['credito'])}. "
            f"[{md_texto(medio['fuente'])}]({medio['fuente_url']}). "
            f"[{md_texto(medio['licencia_img'])}]({medio['licencia_url']})."
        )
    lineas.append("")
    return "\n".join(lineas)


# ── Proyecto Quarto ───────────────────────────────────────────────────────


def yaml_texto(valor: str) -> str:
    """Escalar YAML entrecomillado; el índice trae acentos, `:` y comillas."""
    return '"' + str(valor).replace("\\", "\\\\").replace('"', '\\"') + '"'


def quarto_yml(
    capitulos: list, apendices: list, citacion: banco.Citacion,
    version: str, portada: str,
) -> str:
    lineas = [
        "# GENERADO por scripts/qmd.py — no editar a mano.",
        "# La fuente de verdad es el índice YAML de conceptos/, condiciones/ y",
        "# referencias/.",
        "project:",
        "  type: book",
        "  output-dir: _salida",
        "",
        "book:",
        f"  title: {yaml_texto(banco.TITULO)}",
        f"  subtitle: {yaml_texto(banco.SUBTITULO)}",
        "  author:",
        f"    - name: {yaml_texto(banco.AUTOR)}",
        f"      orcid: {yaml_texto(citacion.orcid)}",
        f"  date: {yaml_texto(date.today().isoformat())}",
        f"  publisher: {yaml_texto(banco.EDITORIAL)}",
        "  language: es",
        # El nombre de salida se declara aquí, no bajo el formato: `libro.pdf`,
        # `libro.tex` y `libro.epub` en vez del título con acentos.
        "  output-file: libro",
        f"  cover-image: {portada}",
        "  chapters:",
    ]
    lineas += [f"    - {nombre}" for nombre in capitulos]
    if apendices:
        lineas.append("  appendices:")
        # La bibliografía se emite ya resuelta y numerada en orden de
        # aparición, no por citeproc: por eso es un capítulo más y no una
        # clave `bibliography:`.
        lineas += [f"    - {nombre}" for nombre in apendices]
    lineas += [
        "",
        # `identifier` y `rights` no se declaran bajo `book:`: no son
        # propiedades válidas de ese esquema, y al nivel superior Quarto las
        # pasa a pandoc ADEMÁS del `epub-metadata.xml`, con lo que el OPF sale
        # con dos `dc:identifier`. El XML es la única autoridad.
        "lang: es",
        f"date-meta: {yaml_texto(date.today().isoformat())}",
        f"version: {yaml_texto(version)}",
        "",
        "format:",
        "  epub:",
        "    toc: true",
        # Nivel 2 = parte → condición. Bajar más metería en el índice cada
        # bloque de cada condición.
        "    toc-depth: 2",
        "    css: epub.css",
        f"    epub-cover-image: {portada}",
        "    epub-metadata: epub-metadata.xml",
        "  pdf:",
        "    documentclass: book",
        # La fuente LaTeX es un entregable, no un intermedio: alimenta el ZIP
        # autocontenido y la verificación de figuras.
        "    keep-tex: true",
        "    pdf-engine: lualatex",
        # FreeSerif cubre ≥ → ± ‰ sin fallback silencioso. Es la misma
        # decisión del preámbulo LuaLaTeX que este proyecto jubila: con
        # pdflatex saldría «Missing character» en cuanto un umbral traiga ≥.
        "    mainfont: FreeSerif",
        "    toc: true",
        "    toc-depth: 2",
        "    geometry: margin=2.5cm",
        # `book` activa \\flushbottom: estira la página hasta el margen
        # inferior repartiendo el sobrante entre los espacios de párrafo. En un
        # índice donde casi cada condición trae una tabla de signos que no se
        # parte, eso deja páginas cortas con tres líneas de aire entre bloques.
        # \\raggedbottom deja la página terminar donde termina el texto.
        "    include-in-header:",
        "      text: |",
        "        \\raggedbottom",
        "  html:",
        "    toc: true",
        "    toc-depth: 2",
        "",
    ]
    return "\n".join(lineas)


def escapar_xml(valor: str) -> str:
    return (
        str(valor).replace("&", "&amp;").replace("<", "&lt;")
        .replace(">", "&gt;").replace('"', "&quot;")
    )


def metadatos_epub(citacion: banco.Citacion, version: str) -> str:
    """Dublin Core del contenedor, para `--epub-metadata`.

    Aporta SOLO lo que pandoc no genera por su cuenta: el DOI con su esquema,
    la licencia con URL, la descripción, la fuente y las materias. Título,
    autor, fecha e idioma siguen llegando por `--metadata` para que pandoc arme
    su portadilla; duplicarlos aquí produce dos `dc:title` en el OPF.
    """
    lineas = [
        f'<dc:identifier opf:scheme="DOI">{escapar_xml(citacion.doi_url)}'
        "</dc:identifier>",
        f'<dc:contributor opf:role="aut">ORCID {escapar_xml(citacion.orcid)}'
        "</dc:contributor>",
        # Quarto no lleva `book: publisher:` al OPF, así que por la ruta Quarto
        # el contenedor salía sin `dc:publisher`.
        f"<dc:publisher>{escapar_xml(banco.EDITORIAL)}</dc:publisher>",
        f"<dc:rights>{escapar_xml(citacion.licencia)} — "
        f"{escapar_xml(citacion.licencia_url)}. Las figuras conservan sus "
        "licencias propias, declaradas en cada pie y en los créditos finales."
        "</dc:rights>",
        f"<dc:description>{escapar_xml(banco.SUBTITULO)}. "
        f"{escapar_xml(banco.AVISO)} Compilación {date.today().isoformat()}, "
        f"versión {escapar_xml(version)}.</dc:description>",
        f"<dc:source>{escapar_xml(citacion.doi_url)}</dc:source>",
        "<dc:type>Text</dc:type>",
    ]
    lineas += [
        f"<dc:subject>{escapar_xml(m)}</dc:subject>" for m in citacion.materias
    ]
    return "\n".join(lineas) + "\n"


def portada_svg(version: str) -> str:
    seguro = escapar_xml(version)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="2560" viewBox="0 0 1600 2560">
<rect width="1600" height="2560" fill="#141b2d"/>
<path d="M0 1900 C380 1760 700 2080 1080 1900 C1300 1795 1440 1780 1600 1840 L1600 2560 L0 2560 Z" fill="#2f5d8c"/>
<path d="M120 470 h300 l70 -130 l90 260 l80 -190 l70 60 h420" fill="none" stroke="#7fc2d8" stroke-width="16" stroke-linejoin="round"/>
<text x="120" y="800" fill="#f2efe6" font-family="FreeSerif,serif" font-size="150">Índice de</text>
<text x="120" y="975" fill="#f2efe6" font-family="FreeSerif,serif" font-size="150">Semiótica Clínica</text>
<text x="125" y="1160" fill="#7fc2d8" font-family="FreeSerif,serif" font-size="60">Conceptos, condiciones y sus cocientes</text>
<text x="125" y="1240" fill="#7fc2d8" font-family="FreeSerif,serif" font-size="60">de verosimilitud, verificados</text>
<text x="125" y="2180" fill="#f2efe6" font-family="FreeSerif,serif" font-size="58">Dr. Alcy Edmundo Torres Guerrero</text>
<text x="125" y="2280" fill="#b9c8d8" font-family="FreeSerif,serif" font-size="40">Power Semiotics · {seguro}</text>
</svg>
'''


def rasterizar_portada(svg: Path, png: Path) -> bool:
    """Convierte la portada a PNG. Devuelve False si no hay con qué.

    La portada es SVG por diseño —es tipográfica y se versiona en texto—, pero
    como portada del contenedor es frágil: Kindle no admite portadas SVG, de
    modo que en varios lectores saldría en blanco. Se declara el PNG cuando hay
    rasterizador; si no lo hay, se cae al SVG en vez de abortar.
    """
    herramienta = shutil.which("rsvg-convert")
    if not herramienta:
        return False
    try:
        subprocess.run(
            [herramienta, "--width=1600", "--keep-aspect-ratio",
             "--format=png", "--output", str(png), str(svg)],
            check=True, capture_output=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return False
    return png.is_file() and png.stat().st_size > 0


# Sin unidades `vh`: los lectores basados en Adobe Digital Editions no las
# soportan y las resuelven como 0, de modo que la imagen queda embebida en el
# contenedor pero invisible en pantalla.
ESTILO = (
    "body{font-family:FreeSerif,serif;line-height:1.45;color:#17212b}"
    "h1{color:#2f5d8c;page-break-before:always}h2{color:#1d3a57}"
    "h3{color:#141b2d}"
    "img{max-width:100%;height:auto;display:block;margin:1.2em auto}"
    "figure{text-align:center;margin:1.4em 0;page-break-inside:avoid}"
    "figcaption{font-size:.85em;color:#46535d;text-align:left;margin-top:.4em}"
    "a{color:#2f5d8c}code{font-family:monospace}"
    "dt{font-weight:bold;margin-top:.6em}dd{margin-left:1.2em}"
    "table{border-collapse:collapse;width:100%}"
    "th,td{border:1px solid #c8d3d8;padding:.35em .5em;text-align:left;"
    "font-size:.85em}"
)


def render(ejecutable: str, proyecto: Path, formato: str, sufijo: str) -> Path:
    """Renderiza el proyecto a un formato y devuelve el archivo producido.

    Compartida por `epub.py` y `libro.py` para que las dos ediciones salgan del
    mismo árbol con la misma invocación.
    """
    subprocess.run(
        [ejecutable, "render", str(proyecto), "--to", formato],
        cwd=proyecto, check=True,
    )
    salidas = sorted((proyecto / "_salida").glob(f"*{sufijo}"))
    if not salidas:
        raise ErrorGeneracion(
            f"quarto no dejó ningún {sufijo} en {proyecto / '_salida'}"
        )
    return salidas[0]


def generar(indice: banco.Indice, raiz: Path, destino: Path) -> dict:
    raiz = raiz.resolve()
    destino = destino.resolve()
    build = (raiz / "build").resolve()
    if not build.is_relative_to(raiz) or destino == build or not destino.is_relative_to(build):
        raise ErrorGeneracion("el proyecto generado debe estar dentro de build/, en un subdirectorio")
    if destino.exists():
        marca = destino / "_quarto.yml"
        if not marca.is_file() or not marca.read_text(encoding="utf-8").startswith("# GENERADO por scripts/qmd.py"):
            raise ErrorGeneracion(f"no se sobrescribe un directorio ajeno al generador: {destino}")
    if not indice.condiciones_por_archivo:
        raise ErrorGeneracion("no hay condiciones/*.yaml: nada que tipografiar")

    citacion = banco.Citacion(raiz)
    version = banco.version_git(raiz)
    citas = banco.Citas(indice)
    figuras: list = []

    if destino.exists():
        shutil.rmtree(destino)
    destino.mkdir(parents=True)

    # El orden importa: el vocabulario y las condiciones se renderizan primero
    # porque son los que pueblan `citas.orden` y `figuras`, de los que salen
    # la bibliografía y los créditos.
    textos = {"vocabulario.qmd": capitulo_vocabulario(indice, figuras, citas)}
    capitulos = ["index.qmd", "vocabulario.qmd"]
    for clase, titulo in banco.CLASES:
        if not indice.condiciones_de_clase(clase):
            continue
        nombre = f"{slug(titulo)}.qmd"
        textos[nombre] = capitulo_clase(indice, clase, titulo, citas, figuras)
        capitulos.append(nombre)

    portadilla_txt = portadilla(citacion, version)
    textos["index.qmd"] = portadilla_txt

    apendices = ["bibliografia.qmd"]
    textos["bibliografia.qmd"] = bibliografia_capitulo(citas)
    if figuras:
        apendices.append("creditos-imagenes.qmd")
        textos["creditos-imagenes.qmd"] = creditos_imagenes(figuras)

    for nombre, texto in textos.items():
        (destino / nombre).write_text(texto, encoding="utf-8")

    # El libro aplanado NO es un segundo ensamblado: es la concatenación
    # literal de los mismos capítulos que consume Quarto. Existe porque Quarto
    # no está en todos los entornos; si diverge, es un fallo de este script.
    orden_plano = capitulos + apendices
    plano = "\n\n".join(textos[nombre] for nombre in orden_plano)
    (destino / "libro-plano.md").write_text(plano, encoding="utf-8")

    svg = destino / "portada.svg"
    svg.write_text(portada_svg(version), encoding="utf-8")
    portada = (
        "portada.png"
        if rasterizar_portada(svg, destino / "portada.png")
        else "portada.svg"
    )

    (destino / "_quarto.yml").write_text(
        quarto_yml(capitulos, apendices, citacion, version, portada),
        encoding="utf-8",
    )
    (destino / "epub.css").write_text(ESTILO, encoding="utf-8")
    (destino / "epub-metadata.xml").write_text(
        metadatos_epub(citacion, version), encoding="utf-8"
    )
    # `refs.bib` viaja dentro del paquete LaTeX aunque el libro ya no use
    # biblatex: es el archivo que citan por `clave_bibtex` las fichas de
    # biosemiotics.
    (destino / "refs.bib").write_text(banco.build_bibtex(indice), encoding="utf-8")

    # Las imágenes viajan dentro del proyecto para que sea autocontenido, pero
    # conservan su ruta relativa: `archivo_local` sigue siendo la única
    # autoridad y `verificar_publicacion.py` la puede comparar tal cual.
    copiadas = set()
    for _, medio in figuras:
        relativa = medio["archivo_local"]
        interno = destino / relativa
        interno.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(raiz / relativa, interno)
        copiadas.add(relativa)

    return {
        "destino": destino,
        "conceptos": len(indice.conceptos),
        "condiciones": len(indice.condiciones_por_archivo),
        "referencias_citadas": len(citas.orden),
        "referencias": len(indice.referencias),
        "figuras": len(figuras),
        "figuras_detalle": figuras,
        "imagenes_copiadas": len(copiadas),
        "capitulos": capitulos,
        "apendices": apendices,
        "enlaces": sum(
            1 for c in indice.condiciones_por_archivo.values() if c.get("url")
        ),
        "portada": portada,
        "version": version,
        "citacion": citacion,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destino", type=Path, default=Path("build/quarto"))
    parser.add_argument("--raiz", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()

    raiz = args.raiz.resolve()
    destino = args.destino if args.destino.is_absolute() else raiz / args.destino

    informe = generar(banco.Indice(raiz), raiz, destino)

    print(f"→ {destino.relative_to(raiz)}/")
    print(f"  {informe['conceptos']} conceptos · "
          f"{informe['condiciones']} condiciones · "
          f"{len(informe['capitulos'])} capítulos")
    print(f"  {informe['referencias_citadas']} referencias citadas de "
          f"{informe['referencias']} · {informe['figuras']} figuras")
    print(f"  versión {informe['version']}")
    print("  render:  quarto render build/quarto --to epub")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ErrorGeneracion, OSError, KeyError, ValueError) as exc:
        print(f"ERROR QMD: {exc}", file=sys.stderr)
        raise SystemExit(1)
