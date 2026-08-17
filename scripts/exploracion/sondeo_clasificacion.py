import subprocess, os
from collections import Counter

files = [f.strip() for f in subprocess.run(
    ['git', 'ls-files', '*.html'], capture_output=True, text=True).stdout.splitlines() if f.strip()]

AREA = {
    'neurologia': 'Neurología',
    'gastroenterologia': 'Gastroenterología',
    'farmacoterapia_racional': 'Farmacoterapia',
    'medicina_y_datos': 'Medicina y datos',
    'medicina_e_implementacion': 'Implementación',
    'inmunologia': 'Inmunología',
}


def tipo(p):
    n = os.path.basename(p).lower()
    if 'autoevaluacion' in p.lower() or 'evaluacion' in n:
        return 'autoevaluación'
    if 'presentacion' in n:
        return 'presentación'
    if 'taller' in n or 'actividad' in n or 'abp' in n:
        return 'taller'
    if 'masterclass' in n:
        return 'masterclass'
    if 'conocimiento' in n:
        return 'guía'
    if 'simulador' in n or 'reactor' in n or 'dashboard' in n:
        return 'simulador'
    if n == 'index.html':
        return 'índice'
    return 'módulo'


ta, tt = Counter(), Counter()
for f in files:
    p = f.replace(os.sep, '/').replace('\\', '/')
    a = 'raíz' if '/' not in p else AREA.get(p.split('/')[0], '?')
    ta[a] += 1
    tt[tipo(p)] += 1

print('  ÁREA (derivable del directorio):')
for k, v in ta.most_common():
    print(f'    {k:22} {v}')
print('\n  TIPO (derivable del nombre de archivo):')
for k, v in tt.most_common():
    print(f'    {k:22} {v}')
print(f"\n  total: {len(files)}   sin área: {ta.get('?', 0)}")
