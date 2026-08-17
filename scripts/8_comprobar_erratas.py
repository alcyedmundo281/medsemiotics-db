"""Comprueba si alguna referencia del índice tiene errata publicada.

Una retractación es evidente y PubMed la marca como tipo de publicación. Una
errata no: el artículo sigue vigente, pero alguno de sus datos cambió. Para un
índice cuyo valor son las cifras, eso importa tanto como una retractación.
"""
import os, json, sys, io, re, time, pathlib, urllib.request, urllib.parse

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import yaml

DB = pathlib.Path(__file__).resolve().parent.parent
B = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/'

refs = {}
for f in sorted((DB / 'referencias').glob('*.yaml')):
    d = yaml.safe_load(f.read_text(encoding='utf8'))
    pmid = str((d.get('identificadores') or {}).get('pmid') or '')
    if pmid:
        refs[pmid] = {'archivo': f.name, 'titulo': d.get('titulo', '')[:60]}

print(f'referencias con PMID: {len(refs)}')

# ¿cuáles están realmente citadas por una arista?
citadas = set()
for f in (DB / 'condiciones').glob('*.yaml'):
    txt = f.read_text(encoding='utf8')
    citadas.update(re.findall(r'pmid:(\d+)', txt))
for f in (DB / 'conceptos').glob('*.yaml'):
    citadas.update(re.findall(r'pmid:(\d+)', f.read_text(encoding='utf8')))
print(f'referencias citadas por algún registro: {len(citadas)}\n')

ids = list(refs)
texto = ''
for i in range(0, len(ids), 40):
    u = B + 'efetch.fcgi?' + urllib.parse.urlencode(
        {'db': 'pubmed', 'id': ','.join(ids[i:i + 40]), 'retmode': 'text', 'rettype': 'abstract'})
    with urllib.request.urlopen(u, timeout=120) as r:
        texto += r.read().decode('utf8', 'replace') + '\n\n'
    time.sleep(0.4)

con_errata, retractados = [], []
for b in re.split(r'\n\n(?=\d+\. )', texto):
    pm = re.search(r'PMID:\s*(\d+)', b)
    if not pm:
        continue
    pmid = pm.group(1)
    # «Erratum in» señala que ESTE artículo fue corregido.
    er = re.search(r'Erratum in[:\s]+(.{0,110})', b, re.S)
    if er:
        con_errata.append((pmid, ' '.join(er.group(1).split())))
    if re.search(r'Retracted Publication|Retraction in', b, re.I):
        retractados.append(pmid)

print('=== RETRACTADAS ===')
print('  ' + (', '.join(retractados) if retractados else 'ninguna'))

print(f'\n=== CON ERRATA PUBLICADA  ({len(con_errata)}) ===')
for pmid, det in con_errata:
    usada = '  ← CITADA POR UN REGISTRO' if pmid in citadas else '  (no citada)'
    print(f'\n  pmid:{pmid}  {refs[pmid]["titulo"]}{usada}')
    print(f'     {det[:100]}')

if not con_errata:
    print('  ninguna')
