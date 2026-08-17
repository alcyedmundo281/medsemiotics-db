"""Extrae de biosemiotics el material que sembraría el índice.

Solo lectura. Reporta qué campos existen, cuáles alimentan cada tipo de
registro del índice y qué queda sin cubrir.
"""
import sys, io, re, collections, pathlib
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import yaml

# Script de análisis, no del pipeline. Las rutas salen del entorno para no
# incrustar el árbol de una máquina concreta; ver el README de este directorio.
import os as _os
TMP = _os.environ.get('TMP_TRABAJO', '.')
BIOSEMIOTICS = _os.environ.get('BIOSEMIOTICS_REPO', '.')
MEDSEMIOTICS = _os.environ.get('MEDSEMIOTICS_REPO', '.')
HOLONMED_SKILLS = _os.environ.get('HOLONMED_SKILLS', '.')
TAXONOMIA_DIR = _os.environ.get('TAXONOMIA_DIR', '.')


RAIZ = pathlib.Path(BIOSEMIOTICS)

fichas = []
for d in ('conceptos', 'signos', 'casos'):
    for f in sorted((RAIZ / d).glob('*.md')):
        txt = f.read_text(encoding='utf8')
        m = re.match(r'\A---\s*\n(.*?)\n---\s*\n?(.*)\Z', txt, re.S)
        if not m:
            print(f'  SIN FRONT-MATTER: {f.name}')
            continue
        try:
            fm = yaml.safe_load(m.group(1)) or {}
        except Exception as e:
            print(f'  YAML ILEGIBLE: {f.name} -> {e}')
            continue
        fichas.append({'dir': d, 'archivo': f.name, 'fm': fm, 'cuerpo': m.group(2)})

print(f'fichas leídas: {len(fichas)}\n')

# --- qué campos existen y con qué cobertura ---
campos = collections.Counter()
for x in fichas:
    for k in x['fm']:
        campos[k] += 1
print('CAMPO                 presente en')
for k, n in campos.most_common():
    print(f'  {k:20} {n:3}/{len(fichas)}')

# --- mapeo al esquema del índice ---
AL_INDICE = ['significante', 'significado', 'umbral', 'falsos_positivos',
             'sinonimos', 'mesh', 'se_basa_en', 'contrasta_com', 'contrasta_con',
             'titulo', 'titulo_en', 'tipo', 'id']
SE_QUEDA = ['url', 'doi', 'autores', 'medios', 'licencia', 'refs', 'abstract',
            'fecha', 'actualizado', 'version', 'nivel', 'escenario', 'sistema',
            'organo', 'ventana', 'sonda', 'pregunta_clinica', 'descriptores']

print('\n--- cobertura de los campos que van AL ÍNDICE ---')
for c in ['significante', 'significado', 'umbral', 'falsos_positivos', 'mesh',
          'se_basa_en', 'contrasta_con', 'sinonimos']:
    n = sum(1 for x in fichas if x['fm'].get(c))
    print(f'  {c:20} {n:3}/{len(fichas)}')

print('\n--- ¿hay LR, códigos o condiciones en biosemiotics? ---')
for c in ['lr', 'lr_positivo', 'codigos', 'snomed', 'condicion', 'probabilidad_base',
          'factores_riesgo', 'rol']:
    n = sum(1 for x in fichas if c in x['fm'])
    print(f'  {c:20} {n:3}/{len(fichas)}   {"<-- AUSENTE" if n == 0 else ""}')

# --- decision: existe? es prosa? ---
print('\n--- el tercer término de la tríada ---')
n_dec = sum(1 for x in fichas if x['fm'].get('decision'))
print(f'  decision presente    {n_dec:3}/{len(fichas)}')
print('  ejemplos:')
for x in fichas:
    d = x['fm'].get('decision')
    if d:
        print(f'    {x["fm"].get("id","?"):32} {str(d)[:76]}')

# --- referencias ---
refs = collections.Counter()
for x in fichas:
    for r in (x['fm'].get('refs') or []):
        refs[r] += 1
print(f'\n--- referencias citadas: {len(refs)} claves distintas ---')
print(f'  refs.bib contiene: {len(re.findall(r"^@", (RAIZ / "refs.bib").read_text(encoding="utf8"), re.M))} entradas')
bib = (RAIZ / 'refs.bib').read_text(encoding='utf8')
con_pmid = len(re.findall(r'pmid\s*=', bib, re.I))
con_doi = len(re.findall(r'doi\s*=', bib, re.I))
print(f'  con PMID: {con_pmid}   con DOI: {con_doi}')
