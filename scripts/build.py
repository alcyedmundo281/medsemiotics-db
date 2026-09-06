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
conceptos_por_id = {d['id']: d for d in conceptos.values() if d.get('id')}
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
        # La unidad es la que hace dato al corte: 3.5 de potasio en mmol/L y en
        # mg/dL son cuadros distintos. Es aviso y no error porque los umbrales
        # heredados de la semilla no la traen y adivinarla sería inventarla; se
        # repara en la misma pasada que su procedencia.
        if not u.get('unidad'):
            avi(f, 'umbral sin unidad')
    if not d.get('significante'):
        avi(f, 'sin significante')
    # Una figura sin crédito, licencia o archivo real no es una figura: es una
    # atribución inventada o una compilación que falla más tarde en libro.py.
    # No se omiten imágenes ni se infiere su procedencia.
    for i, medio in enumerate(d.get('medios') or [], 1):
        if medio.get('tipo') != 'imagen':
            continue
        REQ_MEDIO = ('descripcion', 'credito', 'fuente', 'fuente_url',
                     'licencia_img', 'licencia_url', 'archivo_local')
        faltantes = [c for c in REQ_MEDIO if not medio.get(c)]
        if faltantes:
            err(f, f'medio {i}: faltan {", ".join(faltantes)}')
            continue
        ruta = (RAIZ / medio['archivo_local']).resolve()
        try:
            ruta.relative_to(RAIZ.resolve())
        except ValueError:
            err(f, f'medio {i}: archivo_local apunta fuera del repositorio')
            continue
        if not ruta.is_file():
            err(f, f'medio {i}: no existe {medio["archivo_local"]}')

for i, n in vistos.items():
    if n > 1:
        errores.append(f'id duplicado: {i} en {n} archivos')

# ── nucleo y balance ─────────────────────────────────────────────────────────
# Claves del balance que NO son un nivel de certeza. Lista blanca a propósito:
# la alternativa —descartar lo que no parezca nivel— convierte en grado de
# certeza cualquier clave nueva que lleve un diccionario, y un nivel de más hace
# el criterio MÁS PERMISIVO. Es el mismo animal que el `tipo` sin lista blanca.
BALANCE_META = ('ref', 'nota', 'fuente')


def revisa_nucleo(f, d, ids_concepto):
    nuc = d.get('nucleo')
    if not isinstance(nuc, dict):
        return
    if not nuc.get('ref'):
        err(f, 'nucleo sin «ref»')
    vistos = 0
    for campo in ('requiere', 'y_al_menos_uno_de'):
        for c in (nuc.get(campo) or []):
            vistos += 1
            # Un código colgado aquí no produce un error visible: produce un
            # núcleo que NUNCA se satisface, y por tanto un diagnóstico que no
            # alcanza ningún nivel de certeza jamás, en silencio.
            if c not in ids_concepto:
                err(f, f'nucleo.{campo} apunta a concepto inexistente: {c}')
    if not vistos:
        err(f, 'nucleo declarado pero vacío: no exige nada')


def revisa_balance(f, d):
    bal = d.get('balance')
    if not isinstance(bal, dict):
        return
    if not bal.get('ref'):
        err(f, 'balance sin «ref»: los enteros los fija el panel, no se derivan')

    niveles = []
    for nombre, regla in bal.items():
        if nombre in BALANCE_META:
            continue
        if not isinstance(regla, dict):
            err(f, f'balance.«{nombre}» no es un nivel ni una clave conocida')
            continue
        for k, v in regla.items():
            if not isinstance(v, int) or isinstance(v, bool) or v < 0:
                err(f, f'balance.{nombre}.{k} = {v!r}: debe ser entero ≥ 0')
        niveles.append((nombre, regla))

    # El orden es SEMÁNTICO: el motor recorre los niveles y se queda con el
    # primero que se satisface. Si «probable» va antes que «establecida», un
    # caso que cumple establecida sale rebajado de grado sin que falle nada.
    for (n1, r1), (n2, r2) in zip(niveles, niveles[1:]):
        a1, a2 = r1.get('apoyos_minimos', 0), r2.get('apoyos_minimos', 0)
        b1, b2 = r1.get('banderas_maximas', 0), r2.get('banderas_maximas', 0)
        if not (isinstance(a1, int) and isinstance(a2, int)
                and isinstance(b1, int) and isinstance(b2, int)):
            continue
        if a2 > a1 or b2 < b1:
            err(f, f'balance: «{n1}» y «{n2}» están en orden incorrecto. Los '
                   f'niveles van del más estricto al más laxo, porque el motor '
                   f'se queda con el primero que se satisface')


# ── el eje `efecto`: qué papel juega el hallazgo en un criterio contado ───────
# Añadido al abrir el eje. Sin esto, las tres claves nuevas entran sin vigilancia
# y la regla que las gobierna vive solo en la documentación, que es justo lo que
# el eje existe para evitar: que la tabla decida y no el juicio de quien puebla.
EFECTOS = ('apoya', 'bandera_roja', 'excluye')
DISPARA = ('presente', 'ausente')
SOSTIENES = ('discriminacion_medida', 'consenso_con_afirmacion',
             'consenso_de_lista', 'mecanismo')
# Una bandera roja empuja hacia la explicación múltiple. Hacerlo sobre la mera
# pertenencia a una lista es multiplicar hipótesis sin necesidad.
AUTORIZAN_BANDERA = ('discriminacion_medida', 'consenso_con_afirmacion')


def revisa_efecto(f, s, donde):
    c = s.get('concepto', '?')
    ef = s.get('efecto')
    ds = s.get('dispara_si')
    so = s.get('sostiene')
    if ef is not None and ef not in EFECTOS:
        err(f, f'{donde} «{c}»: efecto «{ef}» fuera de la taxonomía')
    if ds is not None and ds not in DISPARA:
        err(f, f'{donde} «{c}»: dispara_si «{ds}» fuera de la taxonomía')
    if so is not None and so not in SOSTIENES:
        err(f, f'{donde} «{c}»: sostiene «{so}» fuera de la taxonomía')
    if ef in ('bandera_roja', 'excluye') and not so:
        err(f, f'{donde} «{c}»: efecto «{ef}» exige declarar «sostiene»')
    if ef == 'bandera_roja' and so and so not in AUTORIZAN_BANDERA:
        err(f, f'{donde} «{c}»: «{so}» no autoriza una bandera roja '
               f'(solo {" o ".join(AUTORIZAN_BANDERA)})')
    # La regla dura. mecanismo no puede exigir ref: no hay PMID que diga que un
    # paciente sin apéndice no puede tener apendicitis.
    if so == 'mecanismo':
        if not s.get('motivo'):
            err(f, f'{donde} «{c}»: sostiene «mecanismo» exige «motivo» en prosa')
    elif so and not s.get('ref'):
        err(f, f'{donde} «{c}»: sostiene «{so}» exige «ref» resoluble')
    # Un OR de regresión no es una propiedad del hallazgo: depende de qué
    # covariables entraron. Si el motor bayesiano lo leyera como cociente, lo
    # multiplicaría.
    for campo in ('lr_positivo', 'lr_negativo'):
        v = s.get(campo)
        if isinstance(v, dict) and 'odds_ratio' in v:
            err(f, f'{donde} «{c}»: odds_ratio dentro de {campo}; va en campo aparte')
    orr = s.get('odds_ratio')
    if isinstance(orr, dict):
        if not orr.get('ref'):
            err(f, f'{donde} «{c}»: odds_ratio sin «ref»')
        if not orr.get('covariables'):
            err(f, f'{donde} «{c}»: odds_ratio sin «covariables»; sin ellas no significa nada')


# ── graduación: el eje que convierte un tramo en prosa en un tramo legible ────
# El índice ya traía `tramos`, pero su frontera vivía SOLO en prosa —«linfocitos
# atípicos ≥ 10%», «7 a 10 (riesgo alto)»—. Un consumidor no puede leer eso, así
# que el valor volvía a ser binario en cuanto salía de aquí. `graduacion` declara
# el eje (qué se gradúa, en qué unidad y cómo se leen los tramos) y cada tramo
# puede traer sus límites como números, sin perder la prosa, que sigue siendo la
# etiqueta del libro.
#
# `lectura` NO se infiere de la forma de los datos, porque las dos formas reales
# son indistinguibles a ojo y significan cosas opuestas:
#
#   disjunto     los tramos son [desde, hasta) y no se solapan. Un valor cae en
#                uno y sólo en uno. Es la forma de las escalas: HEART 0-3 y 7-10
#                son estratos que la fuente midió por separado.
#   acumulativo  cada tramo es UN corte de un solo lado, y los cortes se anidan
#                a propósito: la fuente midió «≥10%», «≥20%» y «≥40%» sobre
#                poblaciones que se contienen unas a otras. El consumidor toma el
#                corte MÁS ESTRICTO que el valor satisface. Partirlos en [10,20)
#                para que no se solapen inventaría tres cocientes que nadie midió,
#                que es exactamente el fallo que este repositorio existe para
#                evitar.
LECTURAS = {'acumulativo', 'disjunto'}
CLAVES_GRADUACION = {'parametro', 'unidad', 'lectura', 'nota'}
# Los dos ejes que puede graduar un tramo. No son intercambiables y no pueden
# convivir en la misma lista: ver el comentario de HM:6006.
EJES_TRAMO = ('umbral', 'umbral_condicion')
INF = float('inf')


def _etiqueta_tramo(t):
    for k in EJES_TRAMO + ('rango',):
        if t.get(k):
            return t[k]
    desde, hasta = t.get('desde'), t.get('hasta')
    if desde is not None and hasta is not None:
        return f'[{desde}, {hasta})'
    if desde is not None:
        return f'≥ {desde}'
    if hasta is not None:
        return f'< {hasta}'
    return '?'


def _solapan(a, b):
    """Dos intervalos semiabiertos [desde, hasta), con los extremos abiertos."""
    a0 = -INF if a.get('desde') is None else a['desde']
    a1 = INF if a.get('hasta') is None else a['hasta']
    b0 = -INF if b.get('desde') is None else b['desde']
    b1 = INF if b.get('hasta') is None else b['hasta']
    return max(a0, b0) < min(a1, b1)


def revisa_graduacion(f, contenedor, donde, concepto=None):
    tramos = [t for t in (contenedor.get('tramos') or []) if isinstance(t, dict)]
    grad = contenedor.get('graduacion')
    # Un tramo sin límites numéricos no es un error: sigue siendo prosa honesta
    # —«linfocitos > 50% y atípicos > 10%» no es un corte sobre un solo eje— y el
    # consumidor dirá en voz alta que no sabe leerlo, en vez de callarlo.
    graduados = [t for t in tramos
                 if t.get('desde') is not None or t.get('hasta') is not None]

    if grad is not None and not isinstance(grad, dict):
        err(f, f'{donde}: «graduacion» debe ser un bloque con parametro, unidad y lectura')
        return
    if graduados and not grad:
        err(f, f'{donde}: hay tramos con «desde»/«hasta» pero falta «graduacion»: '
               f'un número sin unidad ni forma de lectura no es un dato')
        return
    if grad and not graduados:
        err(f, f'{donde}: «graduacion» declarada pero ningún tramo trae «desde» ni '
               f'«hasta»; declara el eje o quítalo, pero no lo dejes sin efecto')
    if not grad:
        return

    sobrantes = sorted(set(grad) - CLAVES_GRADUACION)
    if sobrantes:
        err(f, f'{donde}: graduacion trae claves sin vigilancia: {", ".join(sobrantes)}')
    if not grad.get('unidad'):
        err(f, f'{donde}: graduacion sin «unidad». Un número sin unidad no es un '
               f'dato: 3.5 de potasio en mmol/L y en mg/dL son cuadros distintos')
    lectura = grad.get('lectura')
    if lectura not in LECTURAS:
        err(f, f'{donde}: graduacion.lectura «{lectura}» fuera de la taxonomía '
               f'({" o ".join(sorted(LECTURAS))}). No se infiere: acumulativo y '
               f'disjunto se parecen en el YAML y dicen cosas opuestas')

    # El corte del hallazgo y el corte de la condición son ejes distintos. En la
    # mononucleosis «≥ 10%» y «≥ 20%» son dos intensidades del MISMO hallazgo; en
    # el aneurisma «≥ 3 cm» y «≥ 4 cm» son la MISMA maniobra medida contra dos
    # diagnósticos distintos. Mezclarlos en una lista deja al consumidor sin
    # forma de saber cuál de las dos cosas está leyendo.
    ejes = {k for t in tramos for k in EJES_TRAMO if t.get(k)}
    if len(ejes) > 1:
        err(f, f'{donde}: los tramos mezclan «umbral» y «umbral_condicion». Uno '
               f'gradúa el hallazgo y el otro redefine la condición contra la que '
               f'se mide; elegir el tramo equivocado desplaza la probabilidad de '
               f'otra cosa')

    numericos = []
    for t in graduados:
        etiqueta = _etiqueta_tramo(t)
        limpio = True
        for k in ('desde', 'hasta'):
            v = t.get(k)
            if v is not None and (isinstance(v, bool) or not isinstance(v, (int, float))):
                err(f, f'{donde}: tramo «{etiqueta}» tiene {k} = {v!r}, que no es un número')
                limpio = False
        if not limpio:
            continue
        desde, hasta = t.get('desde'), t.get('hasta')
        if desde is not None and hasta is not None and not desde < hasta:
            err(f, f'{donde}: tramo «{etiqueta}»: desde ({desde}) no es menor que '
                   f'hasta ({hasta}); el intervalo está vacío')
        numericos.append(t)

    # Un corte estratificado por edad o sexo —creatinina, hemoglobina— no es otro
    # tramo del mismo eje: es otra población medida. Por eso el solapamiento se
    # comprueba DENTRO de cada población y no entre ellas: el corte de varón y el
    # de mujer se solapan por definición y no es un error.
    grupos = collections.defaultdict(list)
    for t in numericos:
        grupos[str(t.get('poblacion') or '')].append(t)

    for poblacion, grupo in grupos.items():
        sufijo = f' [población: {poblacion}]' if poblacion else ''
        if lectura == 'disjunto':
            for i, a in enumerate(grupo):
                for b in grupo[i + 1:]:
                    if _solapan(a, b):
                        err(f, f'{donde}{sufijo}: los tramos «{_etiqueta_tramo(a)}» y '
                               f'«{_etiqueta_tramo(b)}» se solapan. En una lectura '
                               f'disjunta un valor cae en un tramo y sólo en uno')
        elif lectura == 'acumulativo':
            lados, cortes = set(), []
            for t in grupo:
                presentes = [k for k in ('desde', 'hasta') if t.get(k) is not None]
                if len(presentes) != 1:
                    err(f, f'{donde}{sufijo}: el tramo «{_etiqueta_tramo(t)}» declara '
                           f'sus dos extremos. Un tramo acumulativo es UN corte de un '
                           f'solo lado; si la fuente publicó un intervalo cerrado, la '
                           f'lectura es disjunta')
                    continue
                lados.add(presentes[0])
                cortes.append(t[presentes[0]])
            if len(lados) > 1:
                err(f, f'{donde}{sufijo}: los tramos acumulativos mezclan cortes por '
                       f'arriba y por abajo. Los cortes anidados van todos al mismo lado')
            repetidos = sorted({v for v, n in collections.Counter(cortes).items() if n > 1})
            if repetidos:
                err(f, f'{donde}{sufijo}: el corte {repetidos} aparece en dos tramos: '
                       f'dos cocientes para el mismo corte y el consumidor no puede elegir')

    # La unidad canónica vive en el concepto. Cuando el concepto la declara, la
    # arista la comprueba en vez de volver a declararla, y la discrepancia se caza
    # aquí en vez de en una lectura equivocada de un valor de laboratorio.
    umbral_concepto = (concepto or {}).get('umbral') or {}
    for clave in ('parametro', 'unidad'):
        aqui, alli = grad.get(clave), umbral_concepto.get(clave)
        if aqui and alli and str(aqui).strip().lower() != str(alli).strip().lower():
            err(f, f'{donde}: graduacion.{clave} «{aqui}» contradice el umbral del '
                   f'concepto «{concepto.get("id")}», que declara «{alli}»')


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
        revisa_efecto(f, s, 'arista')
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
                err(f, f'tramo «{_etiqueta_tramo(t)}» de «{c}» sin «ref»')
            elif t['ref'] not in ids_ref:
                err(f, f'tramo «{_etiqueta_tramo(t)}» de «{c}» cita «{t["ref"]}», que no está en referencias/')

        revisa_graduacion(f, s, f'arista «{c}»', conceptos_por_id.get(c))

        # Un LR− suelto junto a tramos graduados no dice a qué corte llama
        # «negativo», y ése es justo el número con el que se descarta. Sin
        # declararlo, una prueba sensible negativa descarta contra un umbral que
        # el lector supone y el consumidor adivina.
        graduados = [t for t in (s.get('tramos') or [])
                     if isinstance(t, dict)
                     and (t.get('desde') is not None or t.get('hasta') is not None)]
        ln = s.get('lr_negativo')
        if graduados and isinstance(ln, dict) and not (
                ln.get('umbral') or ln.get('umbral_condicion')):
            err(f, f'«{c}» tiene tramos graduados y un lr_negativo que no declara '
                   f'«umbral»: no se sabe qué corte define «negativo»')

    # Los signos de alarma apuntan fuera de la condición: son los que obligan a
    # estudiar antes de etiquetar. Se validan igual que las aristas — una
    # referencia rota aquí desaparece en silencio, que es el peor fallo posible
    # en el bloque que existe para frenar un diagnóstico precipitado.
    for s in (d.get('signos_de_alarma') or []):
        revisa_efecto(f, s, 'signo de alarma')
        c = s.get('concepto')
        if not c:
            err(f, 'signo de alarma sin «concepto»')
        elif c not in ids_concepto:
            err(f, f'signo de alarma apunta a concepto inexistente: {c}')

    # Las escalas se leen por tramos igual que un analito, y sus tramos son lo
    # único que desplaza la probabilidad de forma decisiva en varias condiciones.
    # Se validan con la misma vara: procedencia por tramo y eje declarado.
    for e in (d.get('escalas') or []):
        nombre = e.get('nombre', '?')
        for t in (e.get('tramos') or []):
            if not t.get('ref'):
                err(f, f'escala «{nombre}», tramo «{_etiqueta_tramo(t)}» sin «ref»')
            elif t['ref'] not in ids_ref:
                err(f, f'escala «{nombre}», tramo «{_etiqueta_tramo(t)}» cita '
                       f'«{t["ref"]}», que no está en referencias/')
        revisa_graduacion(f, e, f'escala «{nombre}»')

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

    revisa_nucleo(f, d, ids_concepto)
    revisa_balance(f, d)

    barre(d)

# Qué referencias sostienen de verdad un dato. Una errata en algo que nadie
# cita todavía es un aviso; en algo que ya sostiene un cociente, es un error.
refs_citadas = set()
for _d in list(condiciones.values()) + list(conceptos.values()):
    def _rec(n):
        if isinstance(n, dict):
            for k, v in n.items():
                if k == 'ref' and isinstance(v, str):
                    refs_citadas.add(v)
                else:
                    _rec(v)
        elif isinstance(n, list):
            for v in n:
                _rec(v)
    _rec(_d)

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
    # Una errata no retracta el artículo, pero puede haber cambiado justo la
    # cifra que citamos. Si nadie la cita todavía es solo un aviso; si ya está
    # sosteniendo un cociente, hay que ir a comprobarla.
    if v.get('errata'):
        if d.get('id') in refs_citadas:
            if not v.get('errata_verificada'):
                errores.append(f'{f}: tiene ERRATA y sostiene un cociente en uso — '
                               f'verifica la cifra contra la corrección: {v["errata"]}')
            else:
                avi(f, f'tiene errata publicada cotejada y verificada ({v["errata"]})')
        else:
            avi(f, f'tiene errata publicada ({v["errata"]}); aún no la cita nadie')

# ── informe ───────────────────────────────────────────────────────────────────

print(f'conceptos    {len(conceptos):5}   con umbral: {sum(1 for d in conceptos.values() if d.get("umbral"))}')
print(f'condiciones  {len(condiciones):5}   aristas: {n_aristas}   con cociente: {n_aristas_con_lr}   valores de LR: {n_con_lr}')
print(f'referencias  {len(referencias):5}   verificadas: {sum(1 for d in referencias.values() if (d.get("verificacion") or {}).get("pubmed"))}')

sin_triada = sum(1 for d in conceptos.values() if not d.get('significante'))
print(f'\n⚠ {sin_triada} conceptos sin significante   (se rellenan al migrar biosemiotics)')

# El backlog conocido —conceptos sin tríada, umbrales heredados sin fuente— es
# ruido de fondo previsible y se resume. Lo demás exige mirarlo: un aviso sobre
# un cociente sospechoso sepultado bajo 147 rutinarios es un aviso que nadie ve.
RUTINA = ('sin significante', 'umbral sin procedencia', 'umbral sin unidad')
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
