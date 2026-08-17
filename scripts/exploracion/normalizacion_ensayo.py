import json, re, sys, io, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

rows = [json.loads(l) for l in open(
    _os.path.join(_os.environ.get('TOPICS_JSONL_DIR','.'), 'consolidated_results_topics.jsonl'), encoding='utf8') if l.strip()]

CONECTOR = r'(and|the|or|with|for|of|in|to|a|is|are|may|it)'

def normaliza(t):
    t = (t or '').strip()
    t = re.sub(r'\s+', ' ', t)
    t = re.sub(r'\.\s+[A-Z].*$', '', t)          # corta la frase siguiente
    t = re.sub(rf'\s+{CONECTOR}$', '', t, flags=re.I)  # conector colgando
    t = t.strip(' .,;:-_―')
    if t.count('(') > t.count(')'): t = t[:t.rfind('(')].strip()
    if t.count(')') > t.count('('): t = t.replace(')', '')
    return t.strip()

def clave(t):
    k = t.lower()
    k = re.sub(r'[^a-z0-9 ]', ' ', k)
    k = re.sub(r'\s+', ' ', k).strip()
    k = re.sub(r'\b(syndromes?|diseases?)\b', '', k).strip()
    k = re.sub(r'e?s$', '', k)                    # plural burdo
    return k

crudos = [r.get('output_text', '') for r in rows]
norm = [normaliza(t) for t in crudos]
norm = [t for t in norm if len(t) > 2 and len(t.split()) <= 8]

grupos = collections.defaultdict(list)
for t in norm:
    grupos[clave(t)].append(t)

canon = sorted({sorted(v, key=len)[0] for v in grupos.values()})

print(f"crudos                     {len(crudos)}")
print(f"únicos crudos              {len(set(crudos))}")
print(f"tras normalizar            {len(set(norm))}")
print(f"tras fusionar variantes    {len(canon)}   <-- temas reales estimados")
print(f"\nreducción: {len(set(crudos))} -> {len(canon)}  ({100 - 100*len(canon)//len(set(crudos))}% era ruido o duplicado)")

print("\n--- ejemplos de fusión (variantes -> canónico) ---")
n = 0
for k, v in grupos.items():
    u = sorted(set(v))
    if len(u) > 1:
        print(f"  {sorted(u, key=len)[0]!r}  <=  {u[1:4]}")
        n += 1
        if n >= 12: break

print(f"\n--- 30 temas canónicos de muestra ---")
import random; random.seed(3)
import os as _os

for t in random.sample(canon, 30):
    print("  ·", t)
