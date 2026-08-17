import json, re, collections, sys, io
import os as _os


sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

RUTA = _os.path.join(_os.environ.get('TOPICS_JSONL_DIR','.'), 'consolidated_results_topics.jsonl')
rows = [json.loads(l) for l in open(RUTA, encoding='utf8') if l.strip()]

def sucio(t):
    """Heurísticas de fragmento: lo que no puede ser un título de tema."""
    m = []
    if t.endswith(('and', 'the', 'or', 'with', 'of', 'in', 'to', 'a')): m.append('termina en conector')
    if re.search(r'[a-z]\s*$', t) and len(t.split()) > 5: m.append('acaba en minúscula')
    if t.count(')') != t.count('('): m.append('paréntesis desparejos')
    if t.endswith(('-', '_', ',', ';', ':')): m.append('acaba en signo')
    if re.search(r'\.\s+[A-Z]', t): m.append('contiene otra frase')
    if len(t.split()) > 9: m.append('demasiado largo')
    if re.match(r'^[a-z]', t): m.append('empieza en minúscula')
    return m

limpios, sucios = [], []
for r in rows:
    t = (r.get('output_text') or '').strip()
    (sucios if sucio(t) else limpios).append(t)

print(f"TOTAL registros           {len(rows)}")
print(f"output_text únicos        {len(set(r.get('output_text','').strip() for r in rows))}")
print(f"parecen títulos limpios   {len(limpios)}  ({100*len(limpios)//len(rows)}%)")
print(f"parecen fragmentos        {len(sucios)}  ({100*len(sucios)//len(rows)}%)")

print("\n--- motivos de descarte ---")
mot = collections.Counter()
for r in rows:
    for m in sucio((r.get('output_text') or '').strip()):
        mot[m] += 1
for k, v in mot.most_common():
    print(f"  {k:24} {v}")

print("\n--- 25 FRAGMENTOS (a descartar o reparar) ---")
for t in sorted(set(sucios))[:25]:
    print("  ×", t[:96])

print("\n--- 40 LIMPIOS (candidatos a tema) ---")
for t in sorted(set(limpios))[:40]:
    print("  ✓", t)

# ¿el input trae marcadores útiles?
print("\n--- marcadores presentes en input_text ---")
marc = ['CLINICAL OCCURRENCE', 'KEY SYNDROME', 'KEY DISEASE', 'KEY SIGN', 'KEY SYMPTOM', 'DDX', 'Symptom', 'Sign ']
for m in marc:
    n = sum(1 for r in rows if m in (r.get('input_text') or ''))
    print(f"  {m:22} {n}")
