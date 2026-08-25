#!/usr/bin/env python3
"""incorporar_medio.py — Descarga, audita e incorpora medios de Wikimedia Commons en medsemiotics-db
y opcionalmente sincroniza las imágenes destacadas en el frontend (medsemiotics).

Uso:
    python scripts/incorporar_medio.py --archivo "File:Nombre_En_Commons.jpg" --entidad "HM:3064" --descripcion "..."
    python scripts/incorporar_medio.py --archivo "File:Nombre_En_Commons.jpg" --entidad "HM:6016" --sync-frontend
"""

import argparse
import json
import pathlib
import re
import sys
import urllib.parse
import urllib.request
import yaml

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

RAIZ = pathlib.Path(__file__).resolve().parent.parent
FRONTEND_DIR_DEFECTO = RAIZ.parent / "medsemioitics"

API_COMMONS = "https://commons.wikimedia.org/w/api.php"
UA = {
    "User-Agent": "medsemiotics-atlas/1.0 (https://github.com/alcyedmundo281/medsemiotics-db; mailto:alcyedmundo@gmail.com)"
}


def descargar_info_commons(file_title: str, thumb_width: int = 960) -> dict:
    if not file_title.startswith("File:"):
        file_title = f"File:{file_title}"
    params = {
        "action": "query",
        "titles": file_title,
        "prop": "imageinfo",
        "iiprop": "url|extmetadata|size|sha1|mime",
        "iiurlwidth": thumb_width,
        "format": "json"
    }
    url = f"{API_COMMONS}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        pages = data.get("query", {}).get("pages", {})
        for _, page in pages.items():
            if "imageinfo" in page:
                return page["imageinfo"][0]
    return None


def sincronizar_frontend(frontend_path: pathlib.Path, condicion_id: str, thumb_url: str, desc_url: str, license_name: str, file_title: str):
    """Sincroniza la imagen destacada en assets/data/blog-index.json y assets/data/posts/*.json"""
    if not frontend_path.exists():
        print(f"[AVISO] No se encontró el repositorio frontend en {frontend_path}. Omitiendo sincronización.")
        return

    blog_index_file = frontend_path / "assets" / "data" / "blog-index.json"
    if not blog_index_file.exists():
        print(f"[AVISO] No se encontró {blog_index_file}. Omitiendo.")
        return

    posts = json.loads(blog_index_file.read_text(encoding="utf-8"))
    cid_limpio = condicion_id.replace(":", "")
    slug_modificado = None

    for p in posts:
        if p.get("id", "").startswith(cid_limpio) or (p.get("grounding_badge") and condicion_id in p["grounding_badge"]):
            p["featured_image"] = thumb_url
            p["image_source"] = desc_url
            p["image_license"] = license_name
            p["image_title"] = file_title
            slug_modificado = p.get("slug")
            print(f"✓ Frontend blog-index.json actualizado para {p.get('title')} ({p.get('id')})")

    blog_index_file.write_text(json.dumps(posts, indent=2, ensure_ascii=False), encoding="utf-8")

    if slug_modificado:
        post_json = frontend_path / "assets" / "data" / "posts" / f"{slug_modificado}.json"
        if post_json.exists():
            post_data = json.loads(post_json.read_text(encoding="utf-8"))
            post_data["featured_image"] = thumb_url
            post_data["image_source"] = desc_url
            post_data["image_license"] = license_name
            post_data["image_title"] = file_title
            post_json.write_text(json.dumps(post_data, indent=2, ensure_ascii=False), encoding="utf-8")
            print(f"✓ Frontend post JSON actualizado: {post_json.name}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archivo", required=True, help="Título del archivo en Commons (ej. File:Atypical_lymphocytes_2.jpg)")
    parser.add_argument("--entidad", required=True, help="ID de la entidad (ej. HM:3064 o HM:6016)")
    parser.add_argument("--descripcion", default="", help="Descripción clínica del signo o hallazgo")
    parser.add_argument("--sync-frontend", action="store_true", default=True, help="Sincronizar thumbnail con el frontend medsemiotics (por defecto: True)")
    parser.add_argument("--frontend-dir", type=pathlib.Path, default=FRONTEND_DIR_DEFECTO, help="Ruta al repositorio frontend medsemiotics")
    args = parser.parse_args()

    info = descargar_info_commons(args.archivo)
    if not info:
        sys.exit(f"Error: no se encontró {args.archivo} en Wikimedia Commons")

    ext_meta = info.get("extmetadata", {})
    desc_url = info.get("descriptionurl", "")
    download_url = info.get("url", "")
    thumb_url = info.get("thumburl") or download_url
    raw_name = args.archivo.replace("File:", "").replace(" ", "_")

    artist = ext_meta.get("Artist", {}).get("value", "Desconocido")
    artist = re.sub(r"<[^>]+>", "", artist).strip()
    license_short = ext_meta.get("LicenseShortName", {}).get("value", "CC BY 4.0")
    license_url = ext_meta.get("LicenseUrl", {}).get("value", "")

    # Determinar nombre del archivo local basado en el ID y slug
    suffix = pathlib.Path(raw_name).suffix or ".jpg"
    
    # Buscar el nombre descriptivo de la entidad
    yaml_target = None
    ent_nombre = ""
    for folder in ("conceptos", "condiciones"):
        for f in (RAIZ / folder).glob("*.yaml"):
            text = f.read_text(encoding="utf-8")
            if f"id: '{args.entidad}'" in text or f"id: \"{args.entidad}\"" in text or f"id: {args.entidad}" in text or f.stem.startswith(args.entidad.replace(":", "")):
                yaml_target = f
                data = yaml.safe_load(text) or {}
                ent_nombre = f.stem
                if "-" in ent_nombre:
                    ent_nombre = ent_nombre.split("-", 1)[1]
                break
        if yaml_target:
            break

    slug_archivo = ent_nombre if ent_nombre else args.entidad.replace("HM:", "hm").replace(":", "_").lower()
    local_rel = f"assets/img/{slug_archivo}{suffix}"
    local_abs = RAIZ / local_rel
    local_abs.parent.mkdir(parents=True, exist_ok=True)

    # Descargar archivo a máxima resolución en backend
    print(f"Descargando {download_url} -> {local_abs}...")
    req = urllib.request.Request(download_url, headers=UA)
    with urllib.request.urlopen(req) as resp, open(local_abs, "wb") as out:
        out.write(resp.read())
    print(f"✓ Guardado en backend ({local_abs.stat().st_size} bytes)")

    # Construir bloque medios
    desc_final = args.descripcion or ext_meta.get("ImageDescription", {}).get("value", raw_name)
    desc_final = re.sub(r"<[^>]+>", "", desc_final).strip()

    bloque_medio = {
        "tipo": "imagen",
        "id": f"wikimedia:{raw_name}",
        "descripcion": desc_final,
        "credito": artist,
        "fuente": "Wikimedia Commons",
        "fuente_url": desc_url,
        "licencia_img": license_short,
        "licencia_url": license_url,
        "archivo_local": local_rel
    }

    # Guardar en YAML backend
    if yaml_target:
        content = yaml_target.read_text(encoding="utf-8")
        data = yaml.safe_load(content) or {}
        data["medios"] = [bloque_medio]
        yaml_target.write_text(yaml.dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
        print(f"✓ Bloque medios añadido a {yaml_target.name}")
    else:
        print(f"[AVISO] No se encontró archivo YAML para {args.entidad}. Bloque generado:")
        print(yaml.dump({"medios": [bloque_medio]}, allow_unicode=True, sort_keys=False))

    # Sincronizar con el frontend si aplica
    if args.sync_frontend:
        sincronizar_frontend(
            frontend_path=args.frontend_dir,
            condicion_id=args.entidad,
            thumb_url=thumb_url,
            desc_url=desc_url,
            license_name=license_short,
            file_title=raw_name
        )


if __name__ == "__main__":
    main()
