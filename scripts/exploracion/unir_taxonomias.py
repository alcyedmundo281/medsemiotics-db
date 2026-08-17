import json, sys, io, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
D = TAXONOMIA_DIR

def carga(n):
    return [json.loads(l) for l in open(f'{D}/{n}', encoding='utf8') if l.strip()]

A = carga('processed_data_medical_taxonomy.jsonl')            # tiene type
B = carga('processed_data_medical_taxonomy_structured.jsonl')  # tiene differential_diagnosis
C = carga('consolidated_results_finetuning_data.jsonl')        # input/output

print(f'A {len(A)}   B {len(B)}   C {len(C)}')

# ¿alineados fila a fila?
iguales = sum(1 for a, b in zip(A, B) if (a.get('term') or '').strip() == (b.get('key_term') or '').strip())
print(f'\nfilas con term == key_term en la misma posición: {iguales}/{min(len(A),len(B))}'
      f'  ({100*iguales//min(len(A),len(B))}%)')
defs = sum(1 for a, b in zip(A, B) if (a.get('definition') or '')[:200] == (b.get('definition') or '')[:200])
print(f'filas con definition idéntica (primeros 200 ch): {defs}/{min(len(A),len(B))}')

print('\n--- relleno de campos ---')
def relleno(rows, nombre):
    campos = sorted({k for r in rows for k in r})
    print(f'  {nombre}:')
    for c in campos:
        n = sum(1 for r in rows if str(r.get(c) or '').strip())
        print(f'    {c:24} {n:5}/{len(rows)}  ({100*n//len(rows)}%)')
relleno(A, 'taxonomy')
relleno(B, 'structured')

print('\n--- TYPE cruzado con calidad del término ---')
import re
def frag(t):
    return (t.endswith(('and','the','or','with','of','in','to')) or
            t.count('(') != t.count(')') or bool(re.search(r'\.\s+[A-Z]', t)) or
            len(t.split()) > 9 or t.endswith(('-','_',',',';',':')))
por_tipo = collections.defaultdict(lambda: [0, 0])
for a in A:
    t = (a.get('term') or '').strip()
    por_tipo[a.get('type')][1] += 1
    if not frag(t): por_tipo[a.get('type')][0] += 1
for k, (ok, tot) in sorted(por_tipo.items(), key=lambda x: -x[1][1]):
    print(f'  {k:10} limpios {ok:4}/{tot:4}  ({100*ok//tot}%)')

print('\n--- SYNDROME + DISEASE limpios: el temario real ---')
cand = sorted({(a.get('term') or '').strip() for a in A
               if a.get('type') in ('SYNDROME', 'DISEASE') and not frag((a.get('term') or '').strip())})
print(f'  total: {len(cand)}')
import random; random.seed(11)

# Script de análisis, no del pipeline. Las rutas salen del entorno para no
# incrustar el árbol de una máquina concreta; ver el README de este directorio.
import os as _os
TMP = _os.environ.get('TMP_TRABAJO', '.')
BIOSEMIOTICS = _os.environ.get('BIOSEMIOTICS_REPO', '.')
MEDSEMIOTICS = _os.environ.get('MEDSEMIOTICS_REPO', '.')
HOLONMED_SKILLS = _os.environ.get('HOLONMED_SKILLS', '.')
TAXONOMIA_DIR = _os.environ.get('TAXONOMIA_DIR', '.')

for t in random.sample(cand, 25):
    print('    ·', t)

print('\n--- ¿el archivo C aporta algo que no esté en A? ---')
ta = {(a.get('term') or '').strip() for a in A}
tc = {(c.get('output_text') or '').strip() for c in C}
print(f'  términos solo en C: {len(tc - ta)}')
print(f'  términos solo en A: {len(ta - tc)}')
