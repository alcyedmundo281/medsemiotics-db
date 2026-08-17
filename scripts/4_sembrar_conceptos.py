"""Oleada 0 de medsemiotics-db: cimientos.

Genera los registros que no dependen de ninguna decisión pendiente:
  · 74 referencias (ya convertidas y verificadas contra PubMed y CrossRef)
  · 136 conceptos desde el vocabulario semilla de holonmed
  · 21 umbrales de laboratorio, incrustados en el concepto que les corresponde

Los umbrales NO van en un directorio propio: un punto de corte es una propiedad
del hallazgo que define, no una entidad aparte.
"""
import json, re, sys, io, pathlib, shutil, collections
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


import yaml

REPO = pathlib.Path(RAIZ)
VOCAB = pathlib.Path(ruta('HOLONMED_VOCABULARIO'))
SKILLS = pathlib.Path(ruta('HOLONMED_SKILLS'))
REFS = pathlib.Path(os.path.join(RAIZ, 'referencias'))

NL = '\n'


def esc(v):
    s = str(v)
    if s == '':
        return '""'
    if re.search(r'[:#\[\]{},&*?|<>=!%@`"\']', s) or s != s.strip() \
       or s.lower() in ('yes', 'no', 'true', 'false', 'null', 'on', 'off') \
       or re.match(r'^-', s):
        return "'" + s.replace("'", "''") + "'"
    return s


# ── 1 · umbrales de laboratorio, indexados por término ────────────────────────

umbrales = {}
for f in sorted(SKILLS.glob('*.md')):
    m = re.match(r'\A---\s*\n(.*?)\n---\s*\n', f.read_text(encoding='utf8'), re.S)
    if not m:
        continue
    fm = yaml.safe_load(m.group(1)) or {}
    for lab in (fm.get('laboratorio') or []):
        for direccion, clave in (('alto', 'termino_si_alto'), ('bajo', 'termino_si_bajo')):
            termino = lab.get(clave)
            if not termino:
                continue
            cod = (lab.get('codigos') or {}).get('holonmed')
            umbrales.setdefault(cod or termino, {
                'parametro': lab.get('parametro'),
                'direccion': direccion,
                'corte_superior': lab.get('corte_superior'),
                'corte_inferior': lab.get('corte_inferior'),
                'multiplicador': lab.get('multiplicador'),
                'origen': f.stem,
            })
print(f'umbrales de laboratorio recogidos: {len(umbrales)}')

# ── 2 · conceptos desde la semilla ────────────────────────────────────────────

sem = json.loads(VOCAB.read_text(encoding='utf8'))
conceptos = sem['conceptos']
print(f'conceptos en la semilla: {len(conceptos)}  (versión {sem["version"]})')

destino = REPO / 'conceptos'
if destino.exists():
    shutil.rmtree(destino)
destino.mkdir(parents=True)


def slug(t):
    import unicodedata
    t = unicodedata.normalize('NFD', (t or '').lower())
    t = ''.join(c for c in t if unicodedata.category(c) != 'Mn')
    t = re.sub(r'[^a-z0-9]+', '-', t).strip('-')
    return t[:48] or 'sin-termino'


con_umbral = 0
for c in conceptos:
    cod = c['codigo']
    L = [
        '# Concepto del índice. Sembrado desde el vocabulario semilla de holonmed.',
        '# Los códigos HM: son permanentes: no se renumeran ni se reutilizan.',
        '',
        f'id: {esc(cod)}',
        'tipo: concepto',
        f'semantica: {esc(c["semantica"])}',
        f'termino: {esc(c["termino"])}',
    ]
    if c.get('sinonimos'):
        L.append('sinonimos:')
        L += [f'  - {esc(s)}' for s in c['sinonimos']]
    if c.get('padre'):
        L.append(f'padre: {esc(c["padre"])}')

    codigos = {k: v for k, v in c.items() if k in ('icd10', 'snomed', 'hpo') and v}
    L.append('codigos:')
    for k in ('snomed', 'icd10', 'hpo'):
        L.append(f'  {k}: {esc(codigos[k]) if k in codigos else "null"}')

    u = umbrales.get(cod)
    if u:
        con_umbral += 1
        L += ['', 'umbral:', f'  parametro: {esc(u["parametro"])}',
              f'  direccion: {esc(u["direccion"])}']
        if u.get('corte_superior') is not None:
            L.append(f'  corte_superior: {u["corte_superior"]}')
        if u.get('corte_inferior') is not None:
            L.append(f'  corte_inferior: {u["corte_inferior"]}')
        if u.get('multiplicador') is not None:
            L.append(f'  multiplicador: {u["multiplicador"]}')
        L.append('  ref: null   # pendiente: el corte necesita procedencia')

    # La tríada: se rellena al migrar biosemiotics (oleada 1).
    L += ['', 'significante: null', 'significado: null', 'falsos_positivos: []']

    L += ['', 'procedencia:',
          f'  fuente: vocabulario_semilla holonmed v{sem["version"]}',
          '  nota: >-',
          '    Relicenciado a CC0 por el autor para su uso como índice compartido.',
          '    El original se distribuye bajo AGPL-3.0-or-later dentro de holonmed.']

    (destino / f'{cod.replace(":", "")}-{slug(c["termino"])}.yaml').write_text(
        NL.join(L) + NL, encoding='utf8')

print(f'conceptos escritos: {len(list(destino.glob("*.yaml")))}   con umbral: {con_umbral}')

# ── 3 · referencias ───────────────────────────────────────────────────────────

dref = REPO / 'referencias'
if dref.exists():
    shutil.rmtree(dref)
dref.mkdir(parents=True)
n = 0
for f in sorted(REFS.glob('*.yaml')):
    (dref / f.name).write_text(f.read_text(encoding='utf8'), encoding='utf8')
    n += 1
print(f'referencias copiadas: {n}')

# ── 4 · comprobaciones ────────────────────────────────────────────────────────

print('\n--- validación ---')
ids, padres, malos = set(), [], []
for f in sorted(destino.glob('*.yaml')):
    try:
        d = yaml.safe_load(f.read_text(encoding='utf8'))
    except Exception as e:
        malos.append((f.name, str(e)[:60]))
        continue
    ids.add(d['id'])
    if d.get('padre'):
        padres.append((d['id'], d['padre']))
huerfanos = [(h, p) for h, p in padres if p not in ids]
print(f'  YAML válido            {len(list(destino.glob("*.yaml"))) - len(malos)}/{len(list(destino.glob("*.yaml")))}')
print(f'  ids únicos             {len(ids)}')
print(f'  padres colgados        {len(huerfanos)}  {huerfanos[:5] if huerfanos else ""}')
if malos:
    print(f'  ILEGIBLES: {malos}')
