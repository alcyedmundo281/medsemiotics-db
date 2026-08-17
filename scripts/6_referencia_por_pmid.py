"""Crea el registro de una referencia a partir de su PMID.

    python scripts/6_referencia_por_pmid.py 27115266 ebell2016

Verifica contra PubMed (título, año, retractación, errata) y resuelve el DOI en
CrossRef. Es la única vía por la que debe entrar una referencia: escribirla a
mano abre la puerta a citas que nadie comprobó.

Sobre las ERRATAS: una retractación es evidente y PubMed la marca como tipo de
publicación; una errata no. El artículo sigue vigente pero alguna cifra pudo
cambiar, y para un índice cuyo valor son las cifras eso importa igual. Si el
registro cita una referencia con errata, build.py falla.
"""
import json, sys, io, re, time, pathlib, urllib.request, urllib.parse

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

RAIZ = pathlib.Path(__file__).resolve().parent.parent
EUTILS = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/'
UA = 'medsemiotics-index/0.1 (mailto:alcy.torres@powersemiotics.com)'

if len(sys.argv) < 3:
    sys.exit(__doc__)
PMID, CLAVE = sys.argv[1], sys.argv[2]


def esummary(pmid):
    u = EUTILS + 'esummary.fcgi?' + urllib.parse.urlencode(
        {'db': 'pubmed', 'id': pmid, 'retmode': 'json'})
    with urllib.request.urlopen(u, timeout=60) as r:
        d = json.load(r)['result'].get(pmid)
    if not d or d.get('error'):
        sys.exit(f'PubMed no reconoce el PMID {pmid}')
    return d


def efetch(pmid):
    u = EUTILS + 'efetch.fcgi?' + urllib.parse.urlencode(
        {'db': 'pubmed', 'id': pmid, 'retmode': 'text', 'rettype': 'abstract'})
    with urllib.request.urlopen(u, timeout=90) as r:
        return r.read().decode('utf8', 'replace')


def crossref(doi):
    req = urllib.request.Request('https://api.crossref.org/works/' + urllib.parse.quote(doi),
                                 headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)['message']


def esc(v):
    s = str(v)
    return "'" + s.replace("'", "''") + "'" if re.search(r'[:#\[\]{},&*?|<>=!%@`"\']', s) else s


d = esummary(PMID)
bruto = efetch(PMID)
doi = next((x['value'] for x in d.get('articleids', []) if x['idtype'] == 'doi'), '')
autores = [a['name'] for a in d.get('authors', []) if a.get('authtype') == 'Author']
retractado = any('retract' in t.lower() for t in (d.get('pubtype') or [])) \
    or bool(re.search(r'Retraction in', bruto, re.I))
# La cita de la errata acaba en su DOI; sin ese corte el patrón se lleva el
# comienzo del abstract.
m_err = re.search(r'Erratum in[:\s]+(.*?doi:\s*\S+|.{0,90}?\.)', bruto, re.S)
errata = ' '.join(m_err.group(1).split()) if m_err else None


def titulo_errata(cita):
    """Qué corrige la errata, no solo dónde está.

    La diferencia importa: «Data Error» o «Value Errors in Tables and Abstract»
    invalidan las cifras; una corrección de afiliación de autor no. Sin el
    título habría que abrir cada una a mano para saber si descartar el artículo.
    """
    m = re.search(r'doi:\s*(\S+?)\.?$', cita or '')
    if not m:
        return None
    try:
        u = EUTILS + 'esearch.fcgi?' + urllib.parse.urlencode(
            {'db': 'pubmed', 'term': m.group(1) + '[DOI]', 'retmode': 'json'})
        with urllib.request.urlopen(u, timeout=45) as r:
            ids = json.load(r)['esearchresult']['idlist']
        if not ids:
            return None
        t = efetch(ids[0])
        partes = [p.strip() for p in t.split('\n\n') if p.strip()]
        return ' '.join(partes[1].split())[:90] if len(partes) > 1 else None
    except Exception:
        return None


err_titulo = titulo_errata(errata) if errata else None

print(f'PubMed  {d["title"][:74]}')
print(f'  {d.get("source")}  {d.get("pubdate")}  doi {doi}')
print(f'  retractado: {retractado}   errata: {errata or "no"}')
if err_titulo:
    print(f'  la errata corrige: {err_titulo}')

cr_ok, igual = False, False
try:
    m = crossref(doi)
    cr_ok = True
    t_cr = (m.get('title') or [''])[0]
    norm = lambda s: re.sub(r'[^a-z0-9]', '', (s or '').lower())
    igual = norm(t_cr)[:60] == norm(d['title'])[:60]
    print(f'  CrossRef resuelve: sí   título coincide: {igual}')
except Exception as e:
    print(f'  CrossRef: {str(e)[:60]}')

L = ['# Registro de referencia del índice. Verificado contra PubMed y CrossRef.',
     '# Generado por scripts/6_referencia_por_pmid.py — no editar a mano.',
     '',
     f'id: {esc("pmid:" + PMID)}',
     f'clave_bibtex: {esc(CLAVE)}',
     'tipo: articulo',
     f'titulo: {esc(d["title"].rstrip("."))}',
     'autores:']
L += [f'  - {esc(a)}' for a in autores] or ['  []']
L += [f'publicacion: {esc(d.get("source", ""))}',
      f'anio: {d.get("pubdate", "")[:4]}',
      f'volumen: {esc(d.get("volume", ""))}',
      f'paginas: {esc(d.get("pages", ""))}',
      '',
      'identificadores:',
      f'  pmid: {PMID}',
      f'  doi: {esc(doi)}',
      '',
      'verificacion:',
      '  pubmed: true',
      f'  fecha: {esc(time.strftime("%Y-%m-%d"))}',
      f'  retractado: {"true" if retractado else "false"}']
if errata:
    L.append(f'  errata: {esc(errata)}')
    if err_titulo:
        L.append(f'  errata_corrige: {esc(err_titulo)}')
L += [f'  crossref: {"true" if cr_ok else "false"}',
      f'  crossref_titulo_coincide: {"true" if igual else "false"}']
if errata:
    grave = err_titulo and re.search(r'data|value|error|incorrect', err_titulo, re.I)
    L += ['  notas:',
          "    - 'Tiene errata publicada: comprobar las cifras contra la corrección'"]
    if grave:
        L.append("    - 'La errata afecta a DATOS: no transcribir cifras sin cotejarlas'")
elif not igual and cr_ok:
    L += ['  notas:',
          "    - 'CrossRef registra un título distinto; PubMed es la autoridad'"]

destino = RAIZ / 'referencias' / f'pmid-{PMID}.yaml'
destino.write_text('\n'.join(L) + '\n', encoding='utf8')
print(f'\nescrito: referencias/pmid-{PMID}.yaml')
if errata:
    print('  ⚠ tiene errata: verifica la cifra antes de citarla en una arista')
