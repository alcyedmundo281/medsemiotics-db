"""Segunda verificación: resuelve cada DOI contra CrossRef y anota el resultado
en el registro. PubMed confirma que el artículo existe y no está retractado;
CrossRef confirma que el DOI apunta a ese mismo artículo y sigue vivo.
"""
import re, json, sys, io, pathlib, time, urllib.request, urllib.parse

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import os

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def ruta(variable, defecto=None, obligatoria=True):
    """Ruta configurable por variable de entorno.

    Las fuentes externas (biosemiotics, holonmed, la taxonomía) viven fuera de
    este repositorio a propósito: aquí solo se versiona lo derivado.
    """
    v = os.environ.get(variable, defecto)
    if v is None and obligatoria:
        raise SystemExit(
            f'Falta la variable de entorno {variable}.\n'
            f'Ver scripts/README.md para las fuentes que necesita cada paso.')
    return v



DIR = pathlib.Path(os.path.join(RAIZ, 'referencias'))
API = 'https://api.crossref.org/works/'
UA = 'medsemiotics-index/0.1 (mailto:alcy.torres@powersemiotics.com)'


def norm(t):
    return re.sub(r'[^a-z0-9]', '', (t or '').lower())


def campo(texto, clave):
    m = re.search(rf'^{clave}:\s*(.*)$', texto, re.M)
    if not m:
        return ''
    return m.group(1).strip().strip('"')


def crossref(doi):
    req = urllib.request.Request(API + urllib.parse.quote(doi), headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=45) as r:
        return json.load(r).get('message', {})


archivos = sorted(DIR.glob('*.yaml'))
print(f'registros: {len(archivos)}  ·  resolviendo DOI en CrossRef…\n')

ok, difiere, fallo, retract = [], [], [], []

for i, f in enumerate(archivos, 1):
    txt = f.read_text(encoding='utf8')
    doi = re.search(r'^\s*doi:\s*(.*)$', txt, re.M)
    doi = doi.group(1).strip().strip('"') if doi else ''
    titulo = campo(txt, 'titulo')
    clave = campo(txt, 'clave_bibtex')
    if not doi:
        fallo.append((clave, 'sin DOI'))
        continue
    try:
        m = crossref(doi)
        t_cr = (m.get('title') or [''])[0]
        coincide = norm(t_cr)[:60] == norm(titulo)[:60]
        actualizaciones = m.get('update-to') or []
        esta_retractado = any((u.get('type') or '').lower() == 'retraction' for u in actualizaciones)
        if esta_retractado:
            retract.append(clave)
        if coincide:
            ok.append(clave)
        else:
            difiere.append((clave, titulo[:52], t_cr[:52]))
        # anotar en el registro
        nuevo = txt.replace(
            f'  retractado: {"true" if "retractado: true" in txt else "false"}',
            f'  retractado: {"true" if esta_retractado or "retractado: true" in txt else "false"}\n'
            f'  crossref: true\n'
            f'  crossref_titulo_coincide: {"true" if coincide else "false"}', 1)
        f.write_text(nuevo, encoding='utf8')
    except Exception as e:
        fallo.append((clave, str(e)[:60]))
        nuevo = txt.rstrip('\n') + '\n  crossref: false\n'
        f.write_text(nuevo, encoding='utf8')
    if i % 15 == 0:
        print(f'  … {i}/{len(archivos)}')
    time.sleep(0.12)

print(f'\n=== CrossRef ===')
print(f'  DOI resuelto y título coincide   {len(ok)}')
print(f'  DOI resuelto, título difiere     {len(difiere)}')
print(f'  no resolvió                      {len(fallo)}')
print(f'  marcado como retractado          {len(retract)}')
for c, a, b in difiere[:12]:
    print(f'\n  · {c}\n      registro: {a}\n      CrossRef: {b}')
for c, e in fallo[:12]:
    print(f'  · {c}: {e}')
