"""Convierte refs.bib de biosemiotics en registros de referencia del índice.

Un archivo YAML por referencia. Cada registro conserva la clave BibTeX original
porque es la que citan hoy las 29 fichas: sin ella la migración posterior no
puede resolver `refs: [lichtenstein2008]`.

Además contrasta cada PMID contra PubMed. El índice promete referencias
verificadas; una promesa que no se comprueba es una etiqueta.
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



BIB = pathlib.Path(ruta('BIOSEMIOTICS_REFS'))
SALIDA = pathlib.Path(os.path.join(RAIZ, 'referencias'))
EUTILS = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi'

# ── parseo del BibTeX ─────────────────────────────────────────────────────────

def parsea(texto):
    entradas = []
    for bloque in re.finditer(r'@(\w+)\s*\{\s*([^,]+),(.*?)\n\}', texto, re.S):
        tipo, clave, cuerpo = bloque.group(1), bloque.group(2).strip(), bloque.group(3)
        campos = {}
        for m in re.finditer(r'(\w+)\s*=\s*\{(.*?)\}\s*(?:,|\s*$)', cuerpo, re.S):
            campos[m.group(1).lower()] = re.sub(r'\s+', ' ', m.group(2)).strip()
        entradas.append({'tipo': tipo, 'clave': clave, **campos})
    return entradas


def autores(cadena):
    """BibTeX separa autores con ' and '."""
    return [a.strip() for a in re.split(r'\s+and\s+', cadena or '') if a.strip()]


def esc(v):
    """Cita el escalar YAML solo cuando hace falta."""
    s = str(v)
    if s == '':
        return '""'
    if re.search(r'[:#\-\[\]{},&*?|<>=!%@`"\']|^\s|\s$', s) or s.lower() in ('yes', 'no', 'true', 'false', 'null'):
        return '"' + s.replace('\\', '\\\\').replace('"', '\\"') + '"'
    return s


# ── verificación contra PubMed ────────────────────────────────────────────────

def pubmed(pmids):
    """esummary en lote. Devuelve {pmid: {...}}."""
    out = {}
    for i in range(0, len(pmids), 100):
        lote = pmids[i:i + 100]
        url = EUTILS + '?' + urllib.parse.urlencode(
            {'db': 'pubmed', 'id': ','.join(lote), 'retmode': 'json'})
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                d = json.load(r).get('result', {})
            for p in lote:
                if p in d:
                    out[p] = d[p]
        except Exception as e:
            print(f'  aviso: PubMed no respondió para el lote {i//100 + 1}: {str(e)[:70]}')
        time.sleep(0.5)
    return out


def normaliza_titulo(t):
    return re.sub(r'[^a-z0-9]', '', (t or '').lower())


# ── principal ─────────────────────────────────────────────────────────────────

entradas = parsea(BIB.read_text(encoding='utf8'))
print(f'entradas leídas del .bib: {len(entradas)}')

pmids = [e['pmid'] for e in entradas if e.get('pmid')]
print(f'con PMID: {len(pmids)}  ·  consultando PubMed…')
datos = pubmed(pmids)
print(f'respondieron: {len(datos)}/{len(pmids)}')

SALIDA.mkdir(parents=True, exist_ok=True)
for f in SALIDA.glob('*.yaml'):
    f.unlink()

hoy = time.strftime('%Y-%m-%d')
informe = {'ok': [], 'sin_respuesta': [], 'titulo_difiere': [], 'anio_difiere': [], 'retractado': []}

for e in entradas:
    pmid = e.get('pmid', '')
    pm = datos.get(pmid)
    verificado, notas = False, []

    if pm is None:
        informe['sin_respuesta'].append(e['clave'])
    else:
        verificado = True
        if normaliza_titulo(pm.get('title'))[:60] != normaliza_titulo(e.get('title'))[:60]:
            informe['titulo_difiere'].append((e['clave'], e.get('title', '')[:50], (pm.get('title') or '')[:50]))
            notas.append('el título no coincide con PubMed')
        anio_pm = (pm.get('pubdate') or '')[:4]
        if anio_pm and anio_pm != str(e.get('year', '')):
            informe['anio_difiere'].append((e['clave'], e.get('year'), anio_pm))
            notas.append(f'PubMed indica año {anio_pm}')
        tipos = [t.lower() for t in (pm.get('pubtype') or [])]
        if any('retract' in t for t in tipos):
            informe['retractado'].append(e['clave'])
            notas.append('PUBLICACIÓN RETRACTADA')
        if not notas:
            informe['ok'].append(e['clave'])

    lineas = [
        '# Registro de referencia del índice. Generado desde refs.bib de biosemiotics.',
        '# La verificación contrasta el PMID contra PubMed: no se escribe a mano.',
        '',
        f'id: {esc("pmid:" + pmid) if pmid else esc(e["clave"])}',
        f'clave_bibtex: {esc(e["clave"])}',
        'tipo: articulo',
        f'titulo: {esc(e.get("title", ""))}',
        'autores:',
    ]
    lineas += [f'  - {esc(a)}' for a in autores(e.get('author'))] or ['  []']
    lineas += [
        f'publicacion: {esc(e.get("journal", ""))}',
        f'anio: {esc(e.get("year", ""))}',
    ]
    if e.get('volume'):
        lineas.append(f'volumen: {esc(e["volume"])}')
    if e.get('pages'):
        lineas.append(f'paginas: {esc(e["pages"])}')
    lineas += [
        '',
        'identificadores:',
        f'  pmid: {esc(pmid)}',
        f'  doi: {esc(e.get("doi", ""))}',
        '',
        'verificacion:',
        f'  pubmed: {"true" if verificado else "false"}',
        f'  fecha: {esc(hoy)}',
        f'  retractado: {"true" if e["clave"] in informe["retractado"] else "false"}',
    ]
    if notas:
        lineas.append('  notas:')
        lineas += [f'    - {esc(n)}' for n in notas]

    nombre = f'pmid-{pmid}.yaml' if pmid else f'{e["clave"]}.yaml'
    (SALIDA / nombre).write_text('\n'.join(lineas) + '\n', encoding='utf8')

print(f'\nregistros escritos: {len(list(SALIDA.glob("*.yaml")))} en {SALIDA}')
print('\n=== verificación contra PubMed ===')
print(f'  correctas               {len(informe["ok"])}')
print(f'  sin respuesta           {len(informe["sin_respuesta"])}')
print(f'  título no coincide      {len(informe["titulo_difiere"])}')
print(f'  año no coincide         {len(informe["anio_difiere"])}')
print(f'  RETRACTADAS             {len(informe["retractado"])}')
for c in informe['retractado']:
    print(f'      ⚠ {c}')
for c, a, b in informe['titulo_difiere'][:10]:
    print(f'\n  título · {c}\n      .bib:   {a}\n      PubMed: {b}')
for c, a, b in informe['anio_difiere'][:10]:
    print(f'  año · {c}: .bib {a} / PubMed {b}')
if informe['sin_respuesta']:
    print(f'  sin respuesta: {", ".join(informe["sin_respuesta"][:10])}')
