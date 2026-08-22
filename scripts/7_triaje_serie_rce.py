"""Triaje de la serie Rational Clinical Examination.

Descarga los abstracts y clasifica cada artículo por si trae cocientes
extraíbles. No extrae nada: solo dice dónde hay material.
"""
import os, json, sys, io, re, time, urllib.request, urllib.parse, textwrap, pathlib

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
B = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/'
SALIDA = pathlib.Path(os.environ.get('TMP_TRABAJO', '.')) / 'rce'
SALIDA.mkdir(exist_ok=True)

YA_HECHOS = {'27115266', '10411200', '24938565', '9892455', '26547467',
             '10086438', '11147989', '31237649', '25027143', '31846019',
             '23982370'}


def esearch():
    u = B + 'esearch.fcgi?' + urllib.parse.urlencode(
        {'db': 'pubmed', 'term': '"rational clinical examination"[Title] AND JAMA[Journal]',
         'retmax': 100, 'retmode': 'json'})
    return json.load(urllib.request.urlopen(u, timeout=60))['esearchresult']['idlist']


def efetch(ids):
    u = B + 'efetch.fcgi?' + urllib.parse.urlencode(
        {'db': 'pubmed', 'id': ','.join(ids), 'retmode': 'text', 'rettype': 'abstract'})
    with urllib.request.urlopen(u, timeout=120) as r:
        return r.read().decode('utf8', 'replace')


ids = esearch()
print(f'artículos en la serie: {len(ids)}\n')

textos = []
for i in range(0, len(ids), 20):
    textos.append(efetch(ids[i:i + 20]))
    time.sleep(0.4)
todo = '\n\n'.join(textos)
(SALIDA / 'abstracts.txt').write_text(todo, encoding='utf8')

# patrón de cociente con cifra: «LR, 3.1», «likelihood ratio of 12», «LR+ 5.3»
PAT_LR = re.compile(
    r'(?:likelihood ratios?|LR[+\-−]?)[^.]{0,30}?(\d+\.\d+|\b\d{1,3}\b)', re.I)

filas = []
for b in re.split(r'\n\n(?=\d+\. )', todo):
    if not b.strip():
        continue
    pm = re.search(r'PMID:\s*(\d+)', b)
    if not pm:
        continue
    pmid = pm.group(1)
    anio = re.search(r'JAMA[^;]*?((?:19|20)\d{2})', b)
    tit = re.search(r'\.\s+((?:Does|Is|Will|Has|Did|Physical|Clinical|The rational|A primer|Incorrect)[^.]{5,110})', b)
    titulo = ' '.join((tit.group(1) if tit else '').split())
    tiene_abstract = len(b) > 1300
    lrs = PAT_LR.findall(b) if tiene_abstract else []
    filas.append({'pmid': pmid, 'anio': anio.group(1) if anio else '?',
                  'titulo': titulo, 'abstract': tiene_abstract,
                  'n_lr': len(lrs), 'hecho': pmid in YA_HECHOS,
                  'texto': b})

filas.sort(key=lambda x: (-x['n_lr'], x['anio']))

viables = [f for f in filas if f['n_lr'] >= 2 and not f['hecho']]
sin_abs = [f for f in filas if not f['abstract'] and not f['hecho']]
pobres = [f for f in filas if f['abstract'] and f['n_lr'] < 2 and not f['hecho']]

print(f'{"PMID":10} {"año":6} {"LR":4} título')
print('─' * 100)
print(f'\n### VIABLES — abstract con 2 o más cocientes  ({len(viables)})\n')
for f in viables:
    print(f'{f["pmid"]:10} {f["anio"]:6} {f["n_lr"]:<4} {f["titulo"][:74]}')

print(f'\n### SIN ABSTRACT en PubMed — no verificables  ({len(sin_abs)})\n')
for f in sin_abs:
    print(f'{f["pmid"]:10} {f["anio"]:6} {"—":4} {f["titulo"][:74]}')

print(f'\n### CON ABSTRACT pero pocos o ningún cociente  ({len(pobres)})\n')
for f in pobres:
    print(f'{f["pmid"]:10} {f["anio"]:6} {f["n_lr"]:<4} {f["titulo"][:74]}')

print(f'\n### YA INCORPORADOS  ({sum(1 for f in filas if f["hecho"])})')
for f in filas:
    if f['hecho']:
        print(f'{f["pmid"]:10} {f["anio"]:6} {f["n_lr"]:<4} {f["titulo"][:74]}')

json.dump([{k: v for k, v in f.items() if k != 'texto'} for f in filas],
          open(SALIDA / 'triaje.json', 'w', encoding='utf8'), ensure_ascii=False, indent=1)
print(f'\nabstracts guardados en {SALIDA}')
