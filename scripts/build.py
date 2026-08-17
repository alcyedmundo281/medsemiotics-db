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
# no_medible: el hallazgo forma parte de la definición de caso de la condición,
# así que medir su cociente sería sesgo de incorporación —se compara contra un
# patrón de referencia que ya lo contiene—. No es que falte literatura: no puede
# existir. holonmed necesita distinguirlo de no_medido, que sí puede llegar
# mañana en un pull request.
ESTADOS_LR = {'medido', 'no_medido', 'sin_efecto', 'no_medible'}

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

# Dos métricas distintas que conviene no confundir: una arista puede traer LR+
# y LR− a la vez, así que el número de cocientes es mayor que el de aristas que
# tienen alguno.
n_aristas = n_con_lr = n_aristas_con_lr = 0
for f, d in condiciones.items():
    for req in ('id', 'tipo', 'clase', 'termino'):
        if not d.get(req):
            err(f, f'falta «{req}»')
    if d.get('clase') not in CLASES:
        err(f, f'clase «{d.get("clase")}» fuera de la taxonomía')
    for s in (d.get('signos') or []):
        n_aristas += 1
        if s.get('lr_positivo') or s.get('lr_negativo'):
            n_aristas_con_lr += 1
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
        # Declarar algo inmedible obliga a decir por qué: si no, es
        # indistinguible de rendirse ante una búsqueda que salió vacía.
        if estado == 'no_medible' and not s.get('motivo'):
            err(f, f'«{c}» marcado no_medible sin «motivo»')
        if estado == 'no_medible' and (s.get('lr_positivo') or s.get('lr_negativo')):
            err(f, f'«{c}» es no_medible pero trae un LR')
        # Declararlo medido y no traer cociente deja la arista en un limbo que
        # holonmed no sabe interpretar.
        if estado == 'medido' and not (s.get('lr_positivo') or s.get('lr_negativo')):
            err(f, f'«{c}» está marcado medido pero no trae ningún LR')

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
            rango = lr.get('rango') if isinstance(lr, dict) else None
            # Cuando la fuente da un rango entre estudios se guarda el rango: no
            # se promedia. Pero algo tiene que haber.
            if valor is None and not rango:
                err(f, f'{campo} de «{c}» no declara ni «valor» ni «rango»')
            if isinstance(valor, (int, float)) and valor > 100:
                avi(f, f'{campo} de «{c}» = {valor}: por encima de 100 casi siempre es errata')
            # El extremo de un rango merece el mismo escrutinio que un valor
            # suelto: un LR de 250 es casi siempre una serie diminuta.
            if isinstance(rango, list) and any(isinstance(v, (int, float)) and v > 100 for v in rango):
                avi(f, f'{campo} de «{c}» llega a {max(rango)}: revisa si el extremo del rango es real')

        # Los tramos llevan su propia procedencia: un umbral distinto es una
        # medición distinta, y sin ref quedaría fuera de la regla dura.
        for t in (s.get('tramos') or []):
            if not t.get('ref'):
                err(f, f'tramo «{t.get("umbral", "?")}» de «{c}» sin «ref»')
            elif t['ref'] not in ids_ref:
                err(f, f'tramo «{t.get("umbral", "?")}» de «{c}» cita «{t["ref"]}», que no está en referencias/')

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

    # Las reglas combinan varios conceptos en un criterio que no cabe en una
    # arista suelta —la tríada de la meningitis, los criterios de Light—. Sus
    # componentes y su procedencia se validan igual que todo lo demás.
    for r in (d.get('reglas') or []):
        nombre = r.get('nombre', '?')
        if not r.get('ref'):
            err(f, f'regla «{nombre}» sin «ref»')
        elif r['ref'] not in ids_ref:
            err(f, f'regla «{nombre}» cita «{r["ref"]}», que no está en referencias/')
        comp = r.get('componentes') or []
        if not comp:
            err(f, f'regla «{nombre}» sin «componentes»')
        for c in comp:
            if c not in ids_concepto:
                err(f, f'regla «{nombre}» apunta a concepto inexistente: {c}')

    # Barrido recursivo. Cada condición nueva ha traído su propio bloque
    # —tramos, reglas, modificadores, sensibilidad_por_diametro— y perseguirlos
    # uno a uno garantiza que el siguiente entre sin vigilancia. Esta pasada
    # recorre el árbol entero: mire donde mire, un «ref» tiene que resolver y un
    # «concepto» tiene que existir.
    def barre(nodo, ruta=''):
        if isinstance(nodo, dict):
            for k, v in nodo.items():
                aqui = f'{ruta}.{k}' if ruta else k
                if k == 'ref' and isinstance(v, str):
                    if v not in ids_ref:
                        err(f, f'«{aqui}» cita «{v}», que no está en referencias/')
                elif k == 'concepto' and isinstance(v, str):
                    if v not in ids_concepto:
                        err(f, f'«{aqui}» apunta a concepto inexistente: {v}')
                else:
                    barre(v, aqui)
        elif isinstance(nodo, list):
            for i, v in enumerate(nodo):
                barre(v, f'{ruta}[{i}]')

    barre(d)

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
print(f'condiciones  {len(condiciones):5}   aristas: {n_aristas}   con cociente: {n_aristas_con_lr}   valores de LR: {n_con_lr}')
print(f'referencias  {len(referencias):5}   verificadas: {sum(1 for d in referencias.values() if (d.get("verificacion") or {}).get("pubmed"))}')

sin_triada = sum(1 for d in conceptos.values() if not d.get('significante'))
print(f'\n⚠ {sin_triada} conceptos sin significante   (se rellenan al migrar biosemiotics)')

# El backlog conocido —conceptos sin tríada, umbrales heredados sin fuente— es
# ruido de fondo previsible y se resume. Lo demás exige mirarlo: un aviso sobre
# un cociente sospechoso sepultado bajo 147 rutinarios es un aviso que nadie ve.
RUTINA = ('sin significante', 'umbral sin procedencia')
rutina = [a for a in avisos if any(r in a for r in RUTINA)]
atencion = [a for a in avisos if a not in rutina]

if atencion:
    print(f'\n--- REVISAR ({len(atencion)}) ---')
    for a in atencion:
        print(f'  {a}')

if rutina:
    print(f'\n--- backlog conocido ({len(rutina)}) ---')
    resumen = {}
    for a in rutina:
        for r in RUTINA:
            if r in a:
                resumen[r] = resumen.get(r, 0) + 1
    for r, n in sorted(resumen.items(), key=lambda x: -x[1]):
        print(f'  {n:4}  {r}')

if errores:
    print(f'\n--- ERRORES ({len(errores)}) ---')
    for e in errores[:30]:
        print(f'  {e}')
    sys.exit(1)

print('\nsin errores.')
