"""Valida los registros del índice. No modifica nada.

Falla de forma ruidosa: un registro mal formado que se carga en silencio es
exactamente el fallo que este repositorio existe para evitar.

    python scripts/build.py
"""
import sys, io, re, pathlib, collections

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

try:
    import yaml
except ImportError:
    sys.exit('Falta PyYAML:  pip install pyyaml')

RAIZ = pathlib.Path(__file__).resolve().parent.parent

SEMANTICAS = {'raiz', 'agrupacion', 'hallazgo', 'trastorno', 'procedimiento'}
CLASES = {'sindrome', 'enfermedad'}
ROLES = {'manifestacion', 'prueba_sensible', 'prueba_especifica', 'apoyo', 'imagen'}
ESTADOS_LR = {'medido', 'no_medido', 'sin_efecto'}

errores, avisos = [], []


def err(f, m):
    errores.append(f'{f}: {m}')


def avi(f, m):
    avisos.append(f'{f}: {m}')


def carga(directorio):
    d = RAIZ / directorio
    if not d.exists():
        return {}
    out = {}
    for f in sorted(d.glob('*.yaml')):
        try:
            out[f.name] = yaml.safe_load(f.read_text(encoding='utf8')) or {}
        except Exception as e:
            err(f.name, f'YAML ilegible: {str(e)[:80]}')
    return out


conceptos = carga('conceptos')
condiciones = carga('condiciones')
referencias = carga('referencias')

ids_concepto = {d.get('id') for d in conceptos.values() if d.get('id')}
ids_ref = {d.get('id') for d in referencias.values() if d.get('id')}

# ── conceptos ─────────────────────────────────────────────────────────────────

vistos = collections.Counter()
for f, d in conceptos.items():
    for req in ('id', 'tipo', 'semantica', 'termino'):
        if not d.get(req):
            err(f, f'falta «{req}»')
    if d.get('tipo') != 'concepto':
        err(f, f'tipo debe ser «concepto», no «{d.get("tipo")}»')
    if d.get('semantica') not in SEMANTICAS:
        err(f, f'semantica «{d.get("semantica")}» fuera de la taxonomía')
    if not re.match(r'^HM:\d{4}$', str(d.get('id', ''))):
        err(f, f'id «{d.get("id")}» no sigue el patrón HM:NNNN')
    vistos[d.get('id')] += 1
    if d.get('padre') and d['padre'] not in ids_concepto:
        err(f, f'padre «{d["padre"]}» no existe')
    u = d.get('umbral')
    if u:
        if u.get('corte_superior') is None and u.get('corte_inferior') is None:
            err(f, 'umbral sin corte superior ni inferior')
        if not u.get('ref'):
            avi(f, 'umbral sin procedencia (ref)')
    if not d.get('significante'):
        avi(f, 'sin significante')

for i, n in vistos.items():
    if n > 1:
        errores.append(f'id duplicado: {i} en {n} archivos')

# ── condiciones y aristas ─────────────────────────────────────────────────────

n_aristas = n_con_lr = 0
for f, d in condiciones.items():
    for req in ('id', 'tipo', 'clase', 'termino'):
        if not d.get(req):
            err(f, f'falta «{req}»')
    if d.get('clase') not in CLASES:
        err(f, f'clase «{d.get("clase")}» fuera de la taxonomía')
    for s in (d.get('signos') or []):
        n_aristas += 1
        c = s.get('concepto')
        if not c:
            err(f, 'arista sin «concepto»')
        elif c not in ids_concepto:
            err(f, f'arista apunta a concepto inexistente: {c}')
        if s.get('rol') and s['rol'] not in ROLES:
            err(f, f'rol «{s["rol"]}» fuera de la taxonomía')
        estado = s.get('estado_lr')
        if estado and estado not in ESTADOS_LR:
            err(f, f'estado_lr «{estado}» fuera de la taxonomía')
        for campo in ('lr_positivo', 'lr_negativo'):
            lr = s.get(campo)
            if not lr:
                continue
            n_con_lr += 1
            # REGLA DURA: un LR sin procedencia resoluble no entra.
            ref = lr.get('ref') if isinstance(lr, dict) else None
            if not ref:
                err(f, f'{campo} de «{c}» sin «ref»: un LR sin procedencia no entra')
            elif ref not in ids_ref:
                err(f, f'{campo} de «{c}» cita «{ref}», que no está en referencias/')
            valor = lr.get('valor') if isinstance(lr, dict) else lr
            if isinstance(valor, (int, float)) and valor > 100:
                avi(f, f'{campo} de «{c}» = {valor}: por encima de 100 casi siempre es errata')

    # Los signos de alarma apuntan fuera de la condición: son los que obligan a
    # estudiar antes de etiquetar. Se validan igual que las aristas — una
    # referencia rota aquí desaparece en silencio, que es el peor fallo posible
    # en el bloque que existe para frenar un diagnóstico precipitado.
    for s in (d.get('signos_de_alarma') or []):
        c = s.get('concepto')
        if not c:
            err(f, 'signo de alarma sin «concepto»')
        elif c not in ids_concepto:
            err(f, f'signo de alarma apunta a concepto inexistente: {c}')

# ── referencias ───────────────────────────────────────────────────────────────

for f, d in referencias.items():
    for req in ('id', 'titulo', 'identificadores', 'verificacion'):
        if not d.get(req):
            err(f, f'falta «{req}»')
    v = d.get('verificacion') or {}
    if not v.get('pubmed'):
        avi(f, 'no verificada contra PubMed')
    if v.get('retractado'):
        errores.append(f'{f}: RETRACTADA — ninguna arista puede citarla')

# ── informe ───────────────────────────────────────────────────────────────────

print(f'conceptos    {len(conceptos):5}   con umbral: {sum(1 for d in conceptos.values() if d.get("umbral"))}')
print(f'condiciones  {len(condiciones):5}   aristas: {n_aristas}   con LR: {n_con_lr}')
print(f'referencias  {len(referencias):5}   verificadas: {sum(1 for d in referencias.values() if (d.get("verificacion") or {}).get("pubmed"))}')

sin_triada = sum(1 for d in conceptos.values() if not d.get('significante'))
print(f'\n⚠ {sin_triada} conceptos sin significante   (se rellenan al migrar biosemiotics)')

if avisos:
    print(f'\n--- avisos ({len(avisos)}) ---')
    for a in avisos[:15]:
        print(f'  {a}')
    if len(avisos) > 15:
        print(f'  … y {len(avisos) - 15} más')

if errores:
    print(f'\n--- ERRORES ({len(errores)}) ---')
    for e in errores[:30]:
        print(f'  {e}')
    sys.exit(1)

print('\nsin errores.')
