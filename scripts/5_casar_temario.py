"""Casa los términos del temario (inglés) contra los 136 conceptos de la semilla
(español), por cognados grecolatinos.

NO fusiona nada. Produce una hoja revisable: el emparejamiento automático de
vocabularios clínicos en dos idiomas produce falsos positivos peligrosos
—«hiperlipasemia» e «hiperlipemia» se parecen y son cuadros distintos—, así que
cada propuesta lleva su nivel de confianza y se confirma a mano.
"""
import json, csv, re, sys, io, unicodedata, collections, difflib

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



VOCAB = ruta('HOLONMED_VOCABULARIO')
TEMARIO = os.path.join(RAIZ, 'datos', 'temario.csv')
SALIDA = os.path.join(RAIZ, 'datos', 'casamiento.csv')

# Transformaciones que llevan un término inglés a su cognado español. El orden
# importa: las más largas primero.
REGLAS = [
    (r'\bhyper', 'hiper'), (r'\bhypo', 'hipo'),
    (r'\bhaemat', 'hemat'), (r'\bhem', 'hem'),
    (r'\boesoph', 'esof'), (r'\besoph', 'esof'),
    (r'\bpneum', 'neum'), (r'\bpsych', 'psiq'),
    (r'\brhin', 'rin'), (r'\brheum', 'reum'),
    (r'\bsclero', 'esclero'), (r'\bsteno', 'esteno'),
    (r'\bsplen', 'esplen'), (r'\bspondy', 'espondi'),
    (r'\bstom', 'estom'), (r'\bstrept', 'estrept'), (r'\bstaphyl', 'estafil'),
    (r'tachy', 'taqui'), (r'brady', 'bradi'), (r'dys', 'dis'),
    (r'phag', 'fag'), (r'phas', 'fas'), (r'phren', 'fren'), (r'phob', 'fob'),
    (r'ph', 'f'), (r'th', 't'), (r'rrh', 'rr'), (r'ch', 'qu'),
    (r'ae', 'e'), (r'oe', 'e'), (r'y', 'i'), (r'k', 'c'), (r'z', 's'),
    (r'tion\b', 'cion'), (r'sis\b', 'sis'), (r'ous\b', 'oso'),
    (r'ic\b', 'ico'), (r'al\b', 'al'), (r'ary\b', 'ario'),
    # Ajustes finos comprobados contra pares reales: dyspnea/disnea,
    # asthma/asma, pruritus/prurito, splenomegaly/esplenomegalia.
    (r'pnea', 'nea'), (r'stm', 'sm'), (r'us\b', 'o'), (r'i\b', 'ia'),
]

# Pares que un motor de similitud confunde y un clínico jamás. Bloquean el
# emparejamiento aunque la distancia sea mínima.
PROHIBIDOS = [
    ('lipasemia', 'lipemia'), ('natremia', 'potasemia'),
    ('glucemia', 'glucosuria'), ('hematuria', 'hematemesis'),
    ('hiper', 'hipo'), ('amilasa', 'lipasa'),
]


def base(t):
    t = unicodedata.normalize('NFD', (t or '').lower())
    t = ''.join(c for c in t if unicodedata.category(c) != 'Mn')
    return re.sub(r'\s+', ' ', re.sub(r'[^a-z0-9 ]', ' ', t)).strip()


def latiniza(t):
    t = base(t)
    for pat, rep in REGLAS:
        t = re.sub(pat, rep, t)
    t = re.sub(r'(.)\1+', r'\1', t)      # colapsa dobles
    return re.sub(r'\s+', '', t)


def choca(a, b):
    for x, y in PROHIBIDOS:
        if (x in a and y in b) or (y in a and x in b):
            if not (x in a and x in b) and not (y in a and y in b):
                return True
    return False


sem = json.load(open(VOCAB, encoding='utf8'))['conceptos']
tem = list(csv.DictReader(open(TEMARIO, encoding='utf-8-sig')))

# índice de la semilla: término y sinónimos, todos latinizados
indice = {}
for c in sem:
    for txt in [c['termino']] + (c.get('sinonimos') or []):
        indice.setdefault(latiniza(txt), []).append(c)

claves = list(indice)
filas, cuenta = [], collections.Counter()

for t in tem:
    termino = t['termino']
    lat = latiniza(termino)
    prop, conf, motivo = None, '', ''

    if lat in indice:
        prop, conf = indice[lat][0], 'alta'
        motivo = 'cognado exacto'
    else:
        cerca = difflib.get_close_matches(lat, claves, n=1, cutoff=0.88)
        if cerca and len(lat) >= 7:
            cand = indice[cerca[0]][0]
            if choca(lat, cerca[0]):
                motivo = 'BLOQUEADO: par que se confunde'
                conf = 'bloqueada'
                prop = cand
            else:
                prop, conf = cand, 'media'
                motivo = f'cognado aproximado ({difflib.SequenceMatcher(None, lat, cerca[0]).ratio():.2f})'

    cuenta[conf or 'sin coincidencia'] += 1
    filas.append({
        'tipo_temario': t['tipo'],
        'termino_ingles': termino,
        'estado_temario': t['estado'],
        'confianza': conf or 'ninguna',
        'codigo_HM': prop['codigo'] if prop else '',
        'termino_semilla': prop['termino'] if prop else '',
        'semantica': prop['semantica'] if prop else '',
        'motivo': motivo,
        'decision': '',      # a rellenar a mano: confirmar / descartar
    })

filas.sort(key=lambda f: ({'alta': 0, 'media': 1, 'bloqueada': 2, 'ninguna': 3}[f['confianza']],
                          f['tipo_temario'], f['termino_ingles'].lower()))

with open(SALIDA, 'w', encoding='utf-8-sig', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=list(filas[0]))
    w.writeheader()
    w.writerows(filas)

print(f'términos del temario: {len(tem)}')
print(f'conceptos de la semilla: {len(sem)}  ({len(claves)} claves con sinónimos)\n')
for k in ('alta', 'media', 'bloqueada', 'sin coincidencia'):
    print(f'  {k:18} {cuenta[k]:5}')

print('\n--- confianza ALTA (cognado exacto) ---')
for f in [x for x in filas if x['confianza'] == 'alta']:
    print(f'  {f["tipo_temario"]:9} {f["termino_ingles"][:38]:40} -> {f["codigo_HM"]}  {f["termino_semilla"]}')

print('\n--- confianza MEDIA (revisar una a una) ---')
for f in [x for x in filas if x['confianza'] == 'media'][:25]:
    print(f'  {f["termino_ingles"][:38]:40} -> {f["codigo_HM"]}  {f["termino_semilla"][:26]:28} {f["motivo"]}')

blo = [x for x in filas if x['confianza'] == 'bloqueada']
if blo:
    print(f'\n--- BLOQUEADAS por guarda de colisión ({len(blo)}) ---')
    for f in blo:
        print(f'  {f["termino_ingles"][:38]:40} ~ {f["termino_semilla"]}')

print(f'\nescrito: {SALIDA}')
