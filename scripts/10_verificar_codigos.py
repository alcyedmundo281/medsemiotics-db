#!/usr/bin/env python3
"""Verifica los códigos CIE-10 y SNOMED CT del índice contra sus fuentes oficiales.

Comprobar todo el índice (antes de abrir un PR que toque `codigos`):
    python scripts/10_verificar_codigos.py

Solo un registro:
    python scripts/10_verificar_codigos.py --id HM:6006

Buscar el código antes de escribirlo —nunca de memoria—:
    python scripts/10_verificar_codigos.py --buscar-snomed "abdominal aortic aneurysm"
    python scripts/10_verificar_codigos.py --hijos-cie10 I71

Fuentes:
  · CIE-10: navegador de la OMS, versión 2019 (icd.who.int/browse10). Es la
    CIE-10 de la OMS, no la CIE-10-CM estadounidense: K58.9 existe en la CM y no
    en la OMS, que divide K58 en K58.1 a K58.8.
  · SNOMED CT: edición internacional en tx.fhir.org. Un concepto de extensión
    nacional se reconoce por su módulo, no por su número: 13841000119107 tiene
    formato de extensión y está en el módulo central.

Por qué existe. `build.py` no puede saber si un código es real: acepta
cualquier cadena. Un código escrito de memoria parece exactamente igual que uno
comprobado, y otros sistemas lo leen como dato. Este script es la comprobación
que antes se hacía a mano con `curl`, para que dé lo mismo en cualquier equipo.

Qué es error (sale con 1): un código que no existe, o un concepto SNOMED
inactivo. Qué es aviso: una categoría CIE-10 en lugar de un código terminal, un
concepto de extensión nacional, una etiqueta semántica inesperada, o una
etiqueta oficial que no comparte ninguna palabra con `termino_en`. Los avisos
piden mirar, no corregir: a veces el código más próximo es el correcto y la
ficha ya explica por qué en su comentario.

Sale con 2 si no hay red: un fallo de red no es un código falso.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("Falta PyYAML:  pip install pyyaml")

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RAIZ = Path(__file__).resolve().parent.parent
OMS = "https://icd.who.int/browse10/2019/en/"
TX = "https://tx.fhir.org/r4/"
SCT = "http://snomed.info/sct"
MODULO_CENTRAL = "900000000000207008"
UA = "medsemiotics-index/0.1 (mailto:alcy.torres@powersemiotics.com)"


class SinRed(Exception):
    pass


def descargar(url: str, fhir: bool = False):
    cabeceras = {"User-Agent": UA}
    if fhir:
        cabeceras["Accept"] = "application/fhir+json"
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=cabeceras),
                                    timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        # tx.fhir.org responde 404 con un OperationOutcome cuando no halla el
        # código: eso es un resultado, no un fallo de red.
        try:
            return json.load(e)
        except Exception:
            raise SinRed(f"{url}: HTTP {e.code}") from e
    except (urllib.error.URLError, TimeoutError) as e:
        raise SinRed(f"{url}: {e}") from e


# ── CIE-10 (OMS) ──────────────────────────────────────────────────────────────

def consultar_cie10(codigo: str, obtener=descargar) -> dict | None:
    """`{'etiqueta', 'terminal'}` o None si la OMS no conoce el código."""
    datos = obtener(OMS + "JsonGetConcept?" + urllib.parse.urlencode(
        {"ConceptId": codigo, "useHtml": "false"}))
    if not datos:
        return None
    etiqueta = re.sub(r"^\S+\s+", "", datos.get("label", ""))
    return {"etiqueta": etiqueta, "terminal": bool(datos.get("isLeaf"))}


def hijos_cie10(codigo: str, obtener=descargar) -> list:
    datos = obtener(OMS + "JsonGetChildrenConcepts?" + urllib.parse.urlencode(
        {"ConceptId": codigo, "useHtml": "false"})) or []
    return [d.get("label", "") for d in datos]


# ── SNOMED CT (tx.fhir.org) ──────────────────────────────────────────────────

def consultar_snomed(codigo: str, obtener=descargar) -> dict | None:
    """`{'etiqueta', 'fsn', 'activo', 'modulo', 'version'}` o None si no existe."""
    datos = obtener(TX + "CodeSystem/$lookup?" + urllib.parse.urlencode(
        {"system": SCT, "code": codigo}), fhir=True)
    if not datos or datos.get("resourceType") == "OperationOutcome":
        return None
    info = {"etiqueta": None, "fsn": None, "activo": None, "modulo": None, "version": None}
    for p in datos.get("parameter", []):
        nombre = p.get("name")
        if nombre == "display":
            info["etiqueta"] = p.get("valueString")
        elif nombre == "version":
            info["version"] = p.get("valueString", "").rsplit("/", 1)[-1]
        elif nombre == "designation":
            valor = next((x.get("valueString") for x in p.get("part", [])
                          if "valueString" in x), "")
            if re.search(r"\([a-z ]+\)$", valor or "") and not info["fsn"]:
                info["fsn"] = valor
        elif nombre == "property":
            partes = p.get("part", [])
            clave = partes[0].get("valueCode") if partes else None
            valor = partes[1] if len(partes) > 1 else {}
            if clave == "inactive":
                info["activo"] = not valor.get("valueBoolean", False)
            elif clave == "module":
                info["modulo"] = valor.get("valueCode")
    return info


def buscar_snomed(texto: str, obtener=descargar) -> list:
    datos = obtener(TX + "ValueSet/$expand?" + urllib.parse.urlencode(
        {"url": SCT + "?fhir_vs", "filter": texto, "count": 20}), fhir=True)
    return [(c["code"], c["display"])
            for c in (datos or {}).get("expansion", {}).get("contains", [])]


# ── comprobación de un registro ───────────────────────────────────────────────

VACIAS = {"of", "the", "and", "with", "without", "in", "to", "due", "a", "an",
          "unspecified", "other", "disorder", "finding", "nos"}


def palabras(texto: str) -> set:
    """Raíces de cuatro letras: «goitre» y «goiter» son la misma palabra."""
    return {p[:4] for p in re.findall(r"[a-z]+", (texto or "").lower())
            if len(p) > 2 and p not in VACIAS}


def comprobar(registro: dict, obtener=descargar) -> tuple[list, list, list]:
    """Devuelve (informe, errores, avisos) de los códigos de un registro."""
    informe, errores, avisos = [], [], []
    rid = registro.get("id", "?")
    codigos = registro.get("codigos") or {}
    termino_en = registro.get("termino_en") or ""
    es_condicion = registro.get("tipo") == "condicion"

    cie = codigos.get("cie10") or codigos.get("icd10")
    if cie:
        r = consultar_cie10(str(cie), obtener)
        if r is None:
            errores.append(f"{rid}: CIE-10 «{cie}» no existe en la versión 2019 de la OMS")
        else:
            informe.append(f"{rid}  CIE-10 {cie}: {r['etiqueta']}")
            if not r["terminal"]:
                avisos.append(f"{rid}: CIE-10 «{cie}» es una categoría con subcódigos; "
                              f"confirma que la ficha explica por qué no va uno terminal")
            if termino_en and not palabras(r["etiqueta"]) & palabras(termino_en):
                avisos.append(f"{rid}: la etiqueta CIE-10 «{r['etiqueta']}» no comparte "
                              f"ninguna palabra con «{termino_en}»")

    sct = codigos.get("snomed")
    if sct:
        r = consultar_snomed(str(sct), obtener)
        if r is None:
            errores.append(f"{rid}: SNOMED «{sct}» no existe en la edición internacional")
        else:
            informe.append(f"{rid}  SNOMED {sct}: {r['fsn'] or r['etiqueta']} "
                           f"(edición {r['version']})")
            if r["activo"] is False:
                errores.append(f"{rid}: SNOMED «{sct}» está INACTIVO")
            if r["modulo"] and r["modulo"] != MODULO_CENTRAL:
                avisos.append(f"{rid}: SNOMED «{sct}» es de una extensión nacional "
                              f"(módulo {r['modulo']}), no del módulo central")
            esperada = "(disorder)" if es_condicion else "(finding)"
            if r["fsn"] and not r["fsn"].endswith(esperada):
                avisos.append(f"{rid}: SNOMED «{sct}» es «{r['fsn']}»; se esperaba "
                              f"un concepto {esperada}")
            if termino_en and not palabras(r["etiqueta"]) & palabras(termino_en):
                avisos.append(f"{rid}: la etiqueta SNOMED «{r['etiqueta']}» no comparte "
                              f"ninguna palabra con «{termino_en}»")
    return informe, errores, avisos


def registros(raiz: Path) -> list:
    out = []
    for carpeta in ("condiciones", "conceptos"):
        for f in sorted((raiz / carpeta).glob("*.yaml")):
            d = yaml.safe_load(f.read_text(encoding="utf8")) or {}
            c = d.get("codigos") or {}
            if isinstance(c, dict) and any(c.get(k) for k in ("cie10", "icd10", "snomed")):
                out.append(d)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--id", help="solo este registro (HM:NNNN)")
    ap.add_argument("--buscar-snomed", metavar="TEXTO",
                    help="lista conceptos SNOMED cuyo nombre contiene TEXTO")
    ap.add_argument("--hijos-cie10", metavar="CODIGO",
                    help="lista los subcódigos CIE-10 de una categoría o bloque")
    args = ap.parse_args()

    try:
        if args.buscar_snomed:
            for codigo, nombre in buscar_snomed(args.buscar_snomed):
                r = consultar_snomed(codigo)
                marca = "" if r and r["modulo"] == MODULO_CENTRAL else "  [extensión]"
                activo = "" if r and r["activo"] else "  [INACTIVO]"
                print(f"{codigo:>18}  {(r or {}).get('fsn') or nombre}{marca}{activo}")
            return 0
        if args.hijos_cie10:
            for etiqueta in hijos_cie10(args.hijos_cie10):
                print(etiqueta)
            return 0

        todos = registros(RAIZ)
        if args.id:
            todos = [d for d in todos if d.get("id") == args.id]
            if not todos:
                print(f"{args.id}: no existe o no declara ningún código")
                return 1
        errores, avisos = [], []
        for d in todos:
            informe, e, a = comprobar(d)
            for linea in informe:
                print(linea)
            errores += e
            avisos += a
    except SinRed as e:
        print(f"Sin acceso a la fuente oficial ({e}). No se ha verificado nada.")
        return 2

    if avisos:
        print(f"\n--- REVISAR ({len(avisos)}) ---")
        for a in avisos:
            print(f"  {a}")
    if errores:
        print(f"\n--- ERRORES ({len(errores)}) ---")
        for e in errores:
            print(f"  {e}")
        return 1
    print(f"\n{len(todos)} registros con códigos, todos existen y están activos.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
