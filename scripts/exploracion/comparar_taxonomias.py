import json, sys, io, collections, re

# Script de análisis, no del pipeline. Las rutas salen del entorno para no
# incrustar el árbol de una máquina concreta; ver el README de este directorio.
import os as _os
TMP = _os.environ.get('TMP_TRABAJO', '.')
BIOSEMIOTICS = _os.environ.get('BIOSEMIOTICS_REPO', '.')
MEDSEMIOTICS = _os.environ.get('MEDSEMIOTICS_REPO', '.')
HOLONMED_SKILLS = _os.environ.get('HOLONMED_SKILLS', '.')
TAXONOMIA_DIR = _os.environ.get('TAXONOMIA_DIR', '.')

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

D = TAXONOMIA_DIR

def carga(n):
    out, bad = [], 0
    for l in open(f'{D}/{n}', encoding='utf8'):
        l = l.strip()
        if not l: continue
        try: out.append(json.loads(l))
        except Exception: bad += 1
    return out, bad

for n in ['processed_data_medical_taxonomy.jsonl',
          'processed_data_medical_taxonomy_structured.jsonl']:
    rows, bad = carga(n)
    print(f'######## {n}')
    print(f'  registros {len(rows)}  ilegibles {bad}')
    esq = collections.Counter(tuple(sorted(r.keys())) for r in rows)
    for k, v in esq.most_common():
        print(f'  esquema {k} -> {v}')
    campo = 'term' if 'term' in rows[0] else 'key_term'
    if 'type' in rows[0]:
        t = collections.Counter(r.get('type') for r in rows)
        print(f'  TYPE: {dict(t)}')
    terms = [(r.get(campo) or '').strip() for r in rows]
    print(f'  términos únicos {len(set(terms))}')
    # calidad del término
    def frag(t):
        return (t.endswith(('and','the','or','with','of','in','to')) or
                t.count('(') != t.count(')') or
                bool(re.search(r'\.\s+[A-Z]', t)) or
                len(t.split()) > 9 or t.endswith(('-','_',',',';',':')))
    malos = [t for t in terms if frag(t)]
    print(f'  parecen fragmentos {len(malos)}  ({100*len(malos)//len(terms)}%)')
    ld = [len(r.get('definition') or '') for r in rows]
    ld.sort()
    print(f'  definition chars: min {ld[0]} / mediana {ld[len(ld)//2]} / max {ld[-1]}')
    print(f'  sin definition: {sum(1 for r in rows if not (r.get("definition") or "").strip())}')
    print('  --- 20 términos ---')
    for t in sorted(set(terms))[:20]:
        print('    ·', t[:78])
    print()
