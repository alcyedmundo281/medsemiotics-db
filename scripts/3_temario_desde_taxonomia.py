"""Extrae SOLO los términos y su tipo. No se lee ni se copia ninguna definición.

Salida: temario.csv, revisable en bloque. Cada fila es un tema candidato, con las
variantes que se fusionaron y una marca de si necesita repaso humano.
"""
import json, re, csv, sys, io, collections, unicodedata

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



ORIGEN = ruta('TAXONOMIA_JSONL')
SALIDA = os.path.join(RAIZ, 'datos', 'temario.csv')

# Adjetivos y calificadores que nunca son un diagnóstico por sí solos: si quedan
# sueltos, el extractor cortó antes del sustantivo.
CALIFICADORES = {
    'abdominal', 'acute', 'chronic', 'benign', 'malignant', 'bullous', 'disseminated',
    'esophageal', 'facial', 'generalized', 'primary', 'secondary', 'other', 'severe',
    'transient', 'recurrent', 'diffuse', 'localized', 'bilateral', 'unilateral',
    'anterior', 'posterior', 'superior', 'inferior', 'lateral', 'medial', 'sudden',
    'congenital', 'acquired', 'idiopathic', 'systemic', 'focal', 'mixed', 'normal',
    'abnormal', 'increased', 'decreased', 'enlarged', 'painful', 'painless', 'multiple',
    'single', 'isolated', 'persistent', 'progressive', 'intermittent', 'nocturnal',
    'peripheral', 'central', 'proximal', 'distal', 'internuclear', 'radial', 'subphrenic',
}

CONECTORES = r'(and|the|or|with|for|of|in|to|a|an|is|are|was|may|it|that|this|which|but|as|by|from|on|at)'

# ── normalización ──────────────────────────────────────────────────────────────

def normaliza(t):
    """Devuelve (termino_limpio, motivos_de_sospecha)."""
    motivos = []
    t = (t or '').strip()
    t = t.replace('―', '-').replace('—', '-').replace('–', '-')
    t = t.replace('“', '"').replace('”', '"').replace('’', "'")
    t = t.replace('_', ' ')
    t = re.sub(r'\s+', ' ', t).strip()

    # una segunda frase pegada: "Actinic Keratosis. The lesion is..."
    if re.search(r'\.\s+[A-Z]', t):
        t = re.sub(r'\.\s+[A-Z].*$', '', t)
        motivos.append('llevaba otra frase pegada')

    # paréntesis desparejos
    if t.count('(') > t.count(')'):
        t = t[:t.rfind('(')].strip()
        motivos.append('paréntesis sin cerrar')
    elif t.count(')') > t.count('('):
        t = t.replace(')', '').strip()
        motivos.append('paréntesis sobrante')

    # conector colgando al final: "Chronic Diarrhea and"
    nuevo = re.sub(rf'\s+{CONECTORES}$', '', t, flags=re.I)
    if nuevo != t:
        t = nuevo
        motivos.append('cortado: acababa en conector')

    t = t.strip(' .,;:-')

    # frase que sigue en minúscula: "Abdominal Pain with Percussion) and suggests the"
    if len(t.split()) > 4 and re.search(r'\s[a-z]{2,}\s+[a-z]{2,}$', t):
        motivos.append('parece frase, no título')

    return t.strip(), motivos


def clave(t):
    """Clave de fusión: solo ignora puntuación, mayúsculas y acentos.
    NO toca 'syndrome'/'disease': Cushing Syndrome y Cushing Disease son distintos."""
    k = unicodedata.normalize('NFD', t.lower())
    k = ''.join(c for c in k if unicodedata.category(c) != 'Mn')
    k = re.sub(r'[^a-z0-9 ]', ' ', k)
    return re.sub(r'\s+', ' ', k).strip()


# ── carga ──────────────────────────────────────────────────────────────────────

filas = [json.loads(l) for l in open(ORIGEN, encoding='utf8') if l.strip()]
print(f'registros leídos: {len(filas)}  (solo se usan los campos term y type)')

registros = []
for f in filas:
    limpio, motivos = normaliza(f.get('term'))
    if len(limpio) < 3:
        continue
    registros.append({'tipo': f.get('type'), 'termino': limpio,
                      'original': (f.get('term') or '').strip(), 'motivos': motivos})

# ── fusión de variantes (dentro del mismo tipo) ────────────────────────────────

grupos = collections.defaultdict(list)
for r in registros:
    grupos[(r['tipo'], clave(r['termino']))].append(r)

# segunda pasada: plural/singular, solo si ambas formas existen
claves = {k for k in grupos}
fusiones_plural = 0
for (tipo, k) in list(claves):
    for suf in ('s', 'es'):
        if k.endswith(suf):
            base = (tipo, k[:-len(suf)])
            if base in grupos and (tipo, k) in grupos:
                grupos[base].extend(grupos.pop((tipo, k)))
                fusiones_plural += 1
                break

# ── consolidación ──────────────────────────────────────────────────────────────

temas = []
for (tipo, _), miembros in grupos.items():
    variantes = sorted({m['termino'] for m in miembros})
    # el canónico: el más frecuente; a igualdad, el más corto sin marcas de corte
    limpios = [m for m in miembros if not m['motivos']]
    pool = limpios or miembros
    cuenta = collections.Counter(m['termino'] for m in pool)
    canonico = sorted(cuenta.items(), key=lambda x: (-x[1], len(x[0])))[0][0]
    motivos = sorted({mo for m in miembros for mo in m['motivos']})
    # Una sola palabra solo es sospechosa si es un calificador que no puede
    # sostenerse como diagnóstico. 'Amiloidosis' vale; 'Agudo' no.
    if len(canonico.split()) == 1 and canonico.lower() in CALIFICADORES:
        motivos.append('calificador suelto: falta el sustantivo')
    temas.append({
        'tipo': tipo,
        'termino': canonico,
        'estado': 'revisar' if motivos else 'ok',
        'motivo': '; '.join(motivos),
        'variantes': ' | '.join(v for v in variantes if v != canonico),
        'n_registros': len(miembros),
    })

temas.sort(key=lambda t: (t['tipo'], t['termino'].lower()))

with open(SALIDA, 'w', encoding='utf-8-sig', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=['tipo', 'termino', 'estado', 'motivo',
                                       'variantes', 'n_registros'])
    w.writeheader()
    w.writerows(temas)

# ── resumen ────────────────────────────────────────────────────────────────────

print(f'variantes fusionadas por plural: {fusiones_plural}')
print(f'\ntemas tras fusionar: {len(temas)}   (desde {len(registros)} registros)')
print('\n            ok   revisar   total')
for tipo in ('SIGN', 'SYNDROME', 'DISEASE'):
    g = [t for t in temas if t['tipo'] == tipo]
    ok = sum(1 for t in g if t['estado'] == 'ok')
    print(f'  {tipo:9} {ok:4}   {len(g)-ok:5}   {len(g):5}')
ok_tot = sum(1 for t in temas if t['estado'] == 'ok')
print(f'  {"TOTAL":9} {ok_tot:4}   {len(temas)-ok_tot:5}   {len(temas):5}')

print('\n--- motivos de revisión ---')
for m, n in collections.Counter(
        mo for t in temas if t['motivo'] for mo in t['motivo'].split('; ')).most_common():
    print(f'  {m:38} {n}')

print(f'\nescrito: {SALIDA}')
