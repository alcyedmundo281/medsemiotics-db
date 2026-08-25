#!/usr/bin/env python3
"""auditar_medios.py — audita y verifica la trazabilidad legal de imágenes en medsemiotics-db.

Comprueba contra la API de Wikimedia Commons:
  - Existencia del archivo local en assets/img/
  - Coincidencia de hash SHA-1 con Wikimedia Commons
  - URL canónica de la licencia Creative Commons
  - URL pública de la fuente

Uso:
    python scripts/auditar_medios.py            # Reporte
    python scripts/auditar_medios.py --escribir # Aplica correcciones automáticas a los YAML
"""

import argparse
import hashlib
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
import yaml

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

RAIZ = Path(__file__).resolve().parent.parent

API = "https://commons.wikimedia.org/w/api.php"
UA = {
    "User-Agent": "medsemiotics-atlas/1.0 (https://github.com/alcyedmundo281/medsemiotics-db; mailto:alcyedmundo@gmail.com)"
}

LICENCIAS = {
    "CC0 1.0": "https://creativecommons.org/publicdomain/zero/1.0/",
    "CC0": "https://creativecommons.org/publicdomain/zero/1.0/",
    "CC BY 2.0": "https://creativecommons.org/licenses/by/2.0/",
    "CC BY 2.5": "https://creativecommons.org/licenses/by/2.5/",
    "CC BY 3.0": "https://creativecommons.org/licenses/by/3.0/",
    "CC BY 3.0 DE": "https://creativecommons.org/licenses/by/3.0/de/",
    "CC BY 4.0": "https://creativecommons.org/licenses/by/4.0/",
    "CC BY-SA 3.0": "https://creativecommons.org/licenses/by-sa/3.0/",
    "CC BY-SA 4.0": "https://creativecommons.org/licenses/by-sa/4.0/",
    "Dominio público": "https://commons.wikimedia.org/wiki/Commons:Licensing",
    "Public domain": "https://commons.wikimedia.org/wiki/Commons:Licensing",
}

_ultima = [0.0]
PAUSA = 2.0
REINTENTOS = 5


def _api(params: dict) -> dict:
    params = {**params, "format": "json"}
    url = f"{API}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers=UA)
    for intento in range(REINTENTOS):
        espera = PAUSA - (time.monotonic() - _ultima[0])
        if espera > 0:
            time.sleep(espera)
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 429 and intento == REINTENTOS - 1:
                raise RuntimeError("429 tras agotar reintentos")
            if e.code != 429:
                raise
            time.sleep(3 * (intento + 1))
        finally:
            _ultima[0] = time.monotonic()
    raise RuntimeError("inalcanzable")


def por_sha1(ruta: Path):
    if not ruta.exists():
        return None, None
    h = hashlib.sha1(ruta.read_bytes()).hexdigest()
    d = _api({"action": "query", "list": "allimages", "aisha1": h, "ailimit": 1})
    imgs = d.get("query", {}).get("allimages") or []
    return (imgs[0].get("descriptionurl"), "sha1") if imgs else (None, None)


def por_titulo(titulo: str):
    d = _api({"action": "query", "titles": f"File:{titulo}", "prop": "imageinfo", "iiprop": "url"})
    for _, pag in d.get("query", {}).get("pages", {}).items():
        info = pag.get("imageinfo")
        if info:
            return info[0].get("descriptionurl"), "titulo"
    return None, None


def auditar():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--escribir", action="store_true", help="aplica al YAML lo que se pudo verificar")
    args = parser.parse_args()

    img_dir = RAIZ / "assets" / "img"
    resueltos, pendientes = [], []

    for carpeta in ("condiciones", "conceptos"):
        d = RAIZ / carpeta
        if not d.exists():
            continue
        for f in sorted(d.glob("*.yaml")):
            try:
                data = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
            except Exception as e:
                continue

            eid = data.get("id", f.stem)
            medios = data.get("medios") or []
            if not medios:
                continue

            modificado = False
            for idx, medio in enumerate(medios):
                if medio.get("tipo") != "imagen":
                    continue

                ident = str(medio.get("id") or "")
                local_rel = medio.get("archivo_local")
                local_path = (RAIZ / local_rel) if local_rel else None

                # 1. Resolver archivo_local si falta
                if not local_path or not local_path.exists():
                    stem = eid.replace("HM:", "HM").replace(":", "_").lower()
                    for ext in (".jpg", ".jpeg", ".png", ".svg", ".webp"):
                        cand = img_dir / f"{stem}{ext}"
                        if cand.exists():
                            medio["archivo_local"] = f"assets/img/{cand.name}"
                            local_path = cand
                            modificado = True
                            resueltos.append((eid, "archivo_local", medio["archivo_local"]))
                            break

                # 2. Licencia URL
                lic = medio.get("licencia_img", "")
                if lic and not medio.get("licencia_url") and lic in LICENCIAS:
                    medio["licencia_url"] = LICENCIAS[lic]
                    modificado = True
                    resueltos.append((eid, "licencia_url", medio["licencia_url"]))

                # 3. Fuente URL
                if ident.startswith("wikimedia:") and not medio.get("fuente_url"):
                    url = None
                    if local_path and local_path.exists():
                        url, _ = por_sha1(local_path)
                    if not url:
                        titulo = ident.split(":", 1)[1].strip().replace(" ", "_")
                        url, _ = por_titulo(titulo)
                    if url:
                        medio["fuente_url"] = url
                        modificado = True
                        resueltos.append((eid, "fuente_url", url))
                    else:
                        pendientes.append((eid, "fuente_url", "no-resuelve", ident))

            if args.escribir and modificado:
                f.write_text(yaml.dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")

    print(f"VERIFICADOS: {len(resueltos)}")
    for eid, campo, valor in resueltos:
        print(f"  {eid:20} {campo:14} {valor}")

    print(f"\nPENDIENTES (no se rellenan): {len(pendientes)}")
    for eid, campo, via, ident in pendientes:
        print(f"  {eid:20} {campo:14} [{via}] {ident}")

    return 1 if pendientes else 0


if __name__ == "__main__":
    sys.exit(auditar())
