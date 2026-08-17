"""Clasifica las páginas publicadas según encajen o no en el temario clínico
(signos, síndromes, enfermedades) o pertenezcan a otro eje.
"""
import subprocess, re, os, sys, io, collections

# Script de análisis, no del pipeline. Las rutas salen del entorno para no
# incrustar el árbol de una máquina concreta; ver el README de este directorio.
import os as _os
TMP = _os.environ.get('TMP_TRABAJO', '.')
BIOSEMIOTICS = _os.environ.get('BIOSEMIOTICS_REPO', '.')
MEDSEMIOTICS = _os.environ.get('MEDSEMIOTICS_REPO', '.')
HOLONMED_SKILLS = _os.environ.get('HOLONMED_SKILLS', '.')
TAXONOMIA_DIR = _os.environ.get('TAXONOMIA_DIR', '.')

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

REPO = MEDSEMIOTICS
os.chdir(REPO)

paginas = [p.strip().replace('\\', '/') for p in subprocess.run(
    ['git', 'ls-files', '*.html'], capture_output=True, text=True).stdout.splitlines() if p.strip()]

REDIR = {'neurologia/index.html', 'gastroenterologia/index.html',
         'farmacoterapia_racional/index.html', 'medicina_y_datos/index.html',
         'medicina_e_implementacion/index.html', 'inmunologia/index.html'}

def titulo(p):
    try:
        t = open(p, encoding='utf8', errors='ignore').read(6000)
    except Exception:
        return ''
    m = re.search(r'<title>([^<]*)', t, re.I)
    return re.sub(r'\s*[-|·]\s*(Power\s?[Ss]emiotics).*$', '',
                  (m.group(1) if m else '').strip()).strip()

# Nombres de fármaco presentes en el árbol (sufijos de DCI + los explícitos)
SUF_FARMACO = ('mab', 'nib', 'ciclib', 'xaban', 'gliflozina', 'gliptina', 'sartan',
               'prazol', 'statina', 'lidomida', 'peridona', 'cumab', 'zumab', 'ximab')
FARMACOS_EXP = {'apixaban', 'paliperidona', 'tofacitinib', 'ofatumumab', 'ibrutinib',
                'secukinumab', 'guselkumab', 'pembrolizumab', 'nivolumab', 'pomalidomida',
                'faricimab'}

def eje(p):
    d = p.lower()
    base = os.path.basename(d).replace('.html', '')
    if p in REDIR:                       return 'redirección'
    if d.startswith('farmacoterapia_racional/'):
        if base in FARMACOS_EXP or any(base.endswith(s) for s in SUF_FARMACO):
            return 'FÁRMACO'
        return 'FÁRMACO (área)'
    if base in ('medicamentos_cronicos', 'medicamentos_oncologicos'):
        return 'FÁRMACO'
    if d == 'farmacoterapia_racional.html':  return 'FÁRMACO (área)'
    if d.startswith('medicina_y_datos/') or d == 'medicina_y_datos.html':
        return 'MÉTODO / DATOS'
    if d.startswith('medicina_e_implementacion/') or d == 'medicina_e_implementacion.html':
        return 'IMPLEMENTACIÓN'
    if d == 'index.html':                return 'índice'
    return 'CLÍNICO'

grupos = collections.defaultdict(list)
for p in paginas:
    grupos[eje(p)].append((p, titulo(p)))

orden = ['CLÍNICO', 'FÁRMACO', 'FÁRMACO (área)', 'MÉTODO / DATOS',
         'IMPLEMENTACIÓN', 'redirección', 'índice']
print('EJE                     páginas')
for k in orden:
    print(f'  {k:22} {len(grupos.get(k, [])):4}')
print(f'  {"TOTAL":22} {sum(len(v) for v in grupos.values()):4}')

for k in orden:
    if k in ('redirección', 'índice'):
        continue
    print(f'\n=== {k}  ({len(grupos[k])}) ===')
    for p, t in sorted(grupos[k]):
        print(f'  {p:58} {t[:52]}')
