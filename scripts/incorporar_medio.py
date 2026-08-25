#!/usr/bin/env python3
"""incorporar_medio.py — descarga e incorpora una imagen de Wikimedia Commons en medsemiotics-db.

Uso:
    python scripts/incorporar_medio.py --archivo "File:Nombre_En_Commons.jpg" --entidad "HM:6001"
"""

import argparse
import json
import pathlib
import sys
import urllib.parse
import urllib.request
import yaml

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

RAIZ = pathlib.Path(__file__).resolve().parent.parent
API = "https://commons.wikimedia.org/w/api.php"
UA = {
    "User-Agent": "medsemiotics-atlas/1.0 (https://github.com/alcyedmundo281/medsemiotics-db; mailto:alcyedmundo@gmail.com)"
}


def descargar_info_commons(file_title: str) -> dict:
    if not file_title.startswith("File:"):
        file_title = f"File:{file_title}"
    params = {
        "action": "query",
        "titles": file_title,
        "prop": "imageinfo",
        "iiprop": "url|extmetadata|size|sha1|mime",
        "format": "json"
    }
    url = f"{API}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        pages = data.get("query", {}).get("pages", {})
        for _, page in pages.items():
            if "imageinfo" in page:
                return page["imageinfo"][0]
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archivo", required=True, help="Título del archivo en Commons (ej. File:Atypical_lymphocytes_2.jpg)")
    parser.add_argument("--entidad", required=True, help="ID de la entidad a vincular (ej. HM:6003 o HM6003)")
    parser.add_argument("--descripcion", default="", help="Descripción pedagógica del signo/hallazgo")
    args = parser.parse_args()

    info = descargar_info_commons(args.archivo)
    if not info:
        sys.exit(f"Error: no se encontró {args.archivo} en Wikimedia Commons")

    ext_meta = info.get("extmetadata", {})
    desc_url = info.get("descriptionurl", "")
    download_url = info.get("url", "")
    artist = ext_meta.get("Artist", {}).get("value", "Desconocido")
    # Limpiar etiquetas HTML del artista
    artist = re.sub(r"<[^>]+>", "", artist).strip()
    license_short = ext_meta.get("LicenseShortName", {}).get("value", "CC BY 4.0")
    license_url = ext_meta.get("LicenseUrl", {}).get("value", "")

    # Determinar extensión y ruta local
    raw_name = args.archivo.replace("File:", "").replace(" ", "_")
    suffix = pathlib.Path(raw_name).suffix or ".jpg"
    ent_slug = args.entidad.replace("HM:", "HM").replace(":", "_").lower()
    local_rel = f"assets/img/{ent_slug}{suffix}"
    local_abs = RAIZ / local_rel
    local_abs.parent.mkdir(parents=True, exist_ok=True)

    # Descargar imagen local
    print(f"Descargando {download_url} -> {local_abs}...")
    req = urllib.request.Request(download_url, headers=UA)
    with urllib.request.urlopen(req) as resp, open(local_abs, "wb") as out:
        out.write(resp.read())
    print(f"✓ Archivo local guardado ({local_abs.stat().st_size} bytes)")

    # Construir bloque de medio
    bloque_medio = {
        "tipo": "imagen",
        "id": f"wikimedia:{raw_name}",
        "descripcion": args.descripcion or ext_meta.get("ImageDescription", {}).get("value", raw_name),
        "credito": artist,
        "fuente": "Wikimedia Commons",
        "fuente_url": desc_url,
        "licencia_img": license_short,
        "licencia_url": license_url,
        "archivo_local": local_rel
    }

    # Encontrar archivo de la entidad
    yaml_target = None
    for folder in ("condiciones", "conceptos"):
        for f in (RAIZ / folder).glob("*.yaml"):
            text = f.read_text(encoding="utf-8")
            if f"id: '{args.entidad}'" in text or f"id: {args.entidad}" in text or f.stem.startswith(args.entidad):
                yaml_target = f
                break
        if yaml_target:
            break

    if yaml_target:
        data = yaml.safe_load(yaml_target.read_text(encoding="utf-8")) or {}
        data["medios"] = [bloque_medio]
        yaml_target.write_text(yaml.dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
        print(f"✓ Bloque medios añadido exitosamente a {yaml_target.name}")
    else:
        print("\nBloque YAML generado:")
        print(yaml.dump({"medios": [bloque_medio]}, allow_unicode=True, sort_keys=False))


if __name__ == "__main__":
    import re
    main()
