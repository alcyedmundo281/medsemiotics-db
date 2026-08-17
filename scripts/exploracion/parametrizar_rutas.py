"""Sustituye las rutas absolutas del directorio temporal por rutas configurables.

Un script versionado con una ruta a AppData\\Local\\Temp no es reproducible: en
otra máquina, o tras una limpieza de Windows, falla sin explicar por qué.
"""
import re, pathlib, sys, io

# Script de análisis, no del pipeline. Las rutas salen del entorno para no
# incrustar el árbol de una máquina concreta; ver el README de este directorio.
import os as _os
TMP = _os.environ.get('TMP_TRABAJO', '.')
BIOSEMIOTICS = _os.environ.get('BIOSEMIOTICS_REPO', '.')
MEDSEMIOTICS = _os.environ.get('MEDSEMIOTICS_REPO', '.')
HOLONMED_SKILLS = _os.environ.get('HOLONMED_SKILLS', '.')
TAXONOMIA_DIR = _os.environ.get('TAXONOMIA_DIR', '.')

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

DB = pathlib.Path(_os.environ.get('MEDSEMIOTICS_DB', '.'))

CABECERA = '''import os

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def ruta(variable, defecto=None, obligatoria=True):
    """Ruta configurable por variable de entorno.

    Las fuentes externas (biosemiotics, holonmed, la taxonomía) viven fuera de
    este repositorio a propósito: aquí solo se versiona lo derivado.
    """
    v = os.environ.get(variable, defecto)
    if v is None and obligatoria:
        raise SystemExit(
            f'Falta la variable de entorno {variable}.\\n'
            f'Ver scripts/README.md para las fuentes que necesita cada paso.')
    return v

'''

SUSTITUCIONES = {
    '1_referencias_desde_bibtex.py': [
        (r"BIB = pathlib\.Path\(r'[^']*'\)",
         "BIB = pathlib.Path(ruta('BIOSEMIOTICS_REFS'))"),
        (r"SALIDA = pathlib\.Path\(r'[^']*'\)",
         "SALIDA = pathlib.Path(os.path.join(RAIZ, 'referencias'))"),
    ],
    '2_verificar_crossref.py': [
        (r"DIR = pathlib\.Path\(r'[^']*'\)",
         "DIR = pathlib.Path(os.path.join(RAIZ, 'referencias'))"),
    ],
    '3_temario_desde_taxonomia.py': [
        (r"ORIGEN = \(r'[^']*'\s*\n\s*r'[^']*'\)",
         "ORIGEN = ruta('TAXONOMIA_JSONL')"),
        (r"SALIDA = r'[^']*'",
         "SALIDA = os.path.join(RAIZ, 'datos', 'temario.csv')"),
    ],
    '4_sembrar_conceptos.py': [
        (r"REPO = pathlib\.Path\(r'[^']*'\)", "REPO = pathlib.Path(RAIZ)"),
        (r"VOCAB = pathlib\.Path\(r'[^']*'\)",
         "VOCAB = pathlib.Path(ruta('HOLONMED_VOCABULARIO'))"),
        (r"SKILLS = pathlib\.Path\(r'[^']*'\)",
         "SKILLS = pathlib.Path(ruta('HOLONMED_SKILLS'))"),
        (r"REFS = pathlib\.Path\(r'[^']*'\)",
         "REFS = pathlib.Path(os.path.join(RAIZ, 'referencias'))"),
    ],
    '5_casar_temario.py': [
        (r"VOCAB = r'[^']*'", "VOCAB = ruta('HOLONMED_VOCABULARIO')"),
        (r"TEMARIO = r'[^']*'",
         "TEMARIO = os.path.join(RAIZ, 'datos', 'temario.csv')"),
        (r"SALIDA = r'[^']*'",
         "SALIDA = os.path.join(RAIZ, 'datos', 'casamiento.csv')"),
    ],
}

for nombre, reglas in SUSTITUCIONES.items():
    f = DB / 'scripts' / nombre
    s = f.read_text(encoding='utf8')
    # insertar la cabecera tras el bloque de imports de sys/io
    ancla = re.search(r"^sys\.stdout = .*$", s, re.M)
    if ancla and 'def ruta(' not in s:
        s = s[:ancla.end()] + '\n\n' + CABECERA + s[ancla.end():]
    hechos = 0
    for pat, rep in reglas:
        s, n = re.subn(pat, rep, s)
        hechos += n
        if n == 0:
            print(f'  ⚠ {nombre}: sin coincidencia -> {pat[:40]}')
    f.write_text(s, encoding='utf8')
    print(f'  {nombre:34} {hechos} rutas parametrizadas')

# comprobación: ¿queda alguna ruta del temporal?
print('\n--- rutas absolutas restantes ---')
resto = 0
for f in (DB / 'scripts').glob('*.py'):
    for i, l in enumerate(f.read_text(encoding='utf8').splitlines(), 1):
        if 'AppData' in l or 'OneDrive' in l:
            print(f'  {f.name}:{i}  {l.strip()[:80]}')
            resto += 1
print('  ninguna' if not resto else f'  quedan {resto}')
