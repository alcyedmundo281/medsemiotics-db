import subprocess, re, os, sys, io

# Script de análisis, no del pipeline. Las rutas salen del entorno para no
# incrustar el árbol de una máquina concreta; ver el README de este directorio.
import os as _os
TMP = _os.environ.get('TMP_TRABAJO', '.')
BIOSEMIOTICS = _os.environ.get('BIOSEMIOTICS_REPO', '.')
MEDSEMIOTICS = _os.environ.get('MEDSEMIOTICS_REPO', '.')
HOLONMED_SKILLS = _os.environ.get('HOLONMED_SKILLS', '.')
TAXONOMIA_DIR = _os.environ.get('TAXONOMIA_DIR', '.')

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
os.chdir(MEDSEMIOTICS)

paginas = [p.strip().replace(os.sep, '/').replace('\\', '/')
           for p in subprocess.run(['git', 'ls-files', '*.html'],
                                   capture_output=True, text=True).stdout.splitlines() if p.strip()]

REDIR = {'neurologia/index.html', 'gastroenterologia/index.html',
         'farmacoterapia_racional/index.html', 'medicina_y_datos/index.html',
         'medicina_e_implementacion/index.html', 'inmunologia/index.html'}

doc, app, mix = [], [], []
for p in paginas:
    if p in REDIR:
        continue
    s = open(p, encoding='utf8', errors='ignore').read()
    js = sum(len(m) for m in re.findall(r'<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>', s, re.S))
    bundle = ('.bundle.js' in s) or ('ReactDOM' in s)
    interact = bool(re.search(r'addEventListener|onclick=|querySelector', s))
    limpio = re.sub(r'<script.*?</script>|<style.*?</style>', '', s, flags=re.S)
    texto = len(re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', limpio)))
    ratio = js / max(texto, 1)
    if bundle or js > 15000 or ratio > 1.5:
        app.append((p, js, texto))
    elif js < 2000 and not interact:
        doc.append((p, js, texto))
    else:
        mix.append((p, js, texto))

print(f'  APLICACIÓN (no derivable de YAML)  {len(app):3}')
print(f'  MIXTA (texto + interacción)        {len(mix):3}')
print(f'  DOCUMENTO (generable)              {len(doc):3}')
print(f'  {"-"*44}')
print(f'  total                              {len(app)+len(mix)+len(doc):3}')

print('\n  --- APLICACIÓN, las mayores ---')
for p, j, t in sorted(app, key=lambda x: -x[1])[:9]:
    print(f'    {p:56} js={j:6}  texto={t}')
print('\n  --- DOCUMENTO ---')
for p, j, t in sorted(doc, key=lambda x: -x[2])[:9]:
    print(f'    {p:56} js={j:6}  texto={t}')
print('\n  --- MIXTA, las mayores ---')
for p, j, t in sorted(mix, key=lambda x: -x[2])[:9]:
    print(f'    {p:56} js={j:6}  texto={t}')
