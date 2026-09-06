# Mapa maestro — medsemiotics-db

Plano completo del índice: qué registros contiene, de dónde sale cada uno y en
qué orden se pueblan. Este repositorio no publica nada y no tiene prosa; es el
**proveedor** del que se sirven holonmed, biosemiotics y medsemiotics.

**Cómo se usa:** antes de crear un registro, búscalo aquí. Cada término ya sabe
qué tipo es, de qué fuente viene y en qué oleada entra. La taxonomía es fija.

---

## 1. Qué es y qué no es

| | |
|---|---|
| **Es** | conceptos, condiciones y referencias verificadas, en YAML |
| **No es** | prosa, didáctica, prompts, presentación |
| **Licencia** | CC0 — solo hechos: términos, códigos, umbrales, cocientes |
| **Formato** | YAML puro, un registro por archivo. Sin cuerpo Markdown |

La regla que lo define: **si un dato necesita explicarse para entenderse, no
pertenece aquí.** Un umbral, un LR, un sinónimo y un código son hechos. La
fisiopatología es prosa y vive en medsemiotics o en biosemiotics.

### La tríada, repartida

```
signo          → concepto    significante  (lo que se ve)
interpretación → concepto    significado   (la realidad clínica) — sin contexto
decisión       → condición   LR + rol      (Bayes) — depende del contexto
```

Los dos primeros términos pertenecen al concepto y valen siempre. El tercero
pertenece a la arista concepto→condición: la hiperlipasemia tiene LR 26.6 **para
pancreatitis**, no en abstracto.

---

## 2. Taxonomía (los valores fijos del esquema)

### `tipo` de registro
`concepto` · `condicion` · `referencia`

### `semantica` (heredada del vocabulario semilla de holonmed)
`raiz` · `agrupacion` · `hallazgo` · `trastorno` · `procedimiento`

### `clase` de la condición
`sindrome` · `enfermedad`

### `rol` de la arista concepto→condición
Los cinco de holonmed, sin inventar taxonomía nueva:

- **`manifestacion`** — fija la probabilidad pre-test
- **`prueba_sensible`** — su LR− descarta cuando es negativa (SnNOut)
- **`prueba_especifica`** — su LR+ confirma cuando es positiva (SpPIn)
- **`apoyo`** — aporta poco por sí solo
- **`imagen`** — hallazgo de imagen

### `estado_lr`
`medido` · `no_medido` · `sin_efecto` · `no_medible`

La distinción no es cosmética: *no medido* y *medido con LR 1.0* son cosas
distintas, y holonmed necesita saber si ignorar la arista o tratarla como
neutra.

**`no_medible`** se añadió al chocar con la hepatitis viral aguda: cuando el
hallazgo forma parte de la definición de caso, medir su cociente sería sesgo de
incorporación y el número no puede existir. No es que falte literatura. Un
`no_medido` puede llegar mañana en un pull request; un `no_medible` no llegará
nunca, y tratarlo como pendiente deja la ficha eternamente incompleta.
Declararlo obliga a dar `motivo`.

### `efecto` de la arista — el eje nuevo

`apoya` *(por defecto)* · `bandera_roja` · `excluye`

### `dispara_si`

`presente` *(por defecto)* · `ausente`

### `sostiene` — qué clase de evidencia respalda la arista

`discriminacion_medida` · `consenso_con_afirmacion` · `consenso_de_lista` ·
`mecanismo`

Los valores por defecto reproducen exactamente el comportamiento anterior, así
que una arista sin estas claves se comporta como siempre. Las catorce
condiciones existentes no se tocan.

#### Por qué `rol` no puede cargar con esto

Son ejes **ortogonales**. `rol` dice en qué dirección mueve la probabilidad;
`efecto` dice qué papel juega dentro de un criterio contado. Una
`prueba_especifica` puede ser un apoyo, y una apendicectomía previa no es un rol
en absoluto: no es una prueba, no tiene cociente, y sin embargo decide.
`estado_lr` tampoco sirve: sus cuatro valores dicen si el cociente existe, no
con qué polaridad dispara el signo.

#### Regla dura, dependiente de `sostiene`

| `sostiene` | exige |
|---|---|
| `discriminacion_medida` | `ref` resoluble |
| `consenso_con_afirmacion` | `ref` resoluble |
| `consenso_de_lista` | `ref` resoluble |
| `mecanismo` | `motivo` en prosa. **No puede exigir `ref`** |

`mecanismo` no pide cita, y no es una laguna: **no hay ni habrá un PMID que diga
que un paciente sin apéndice no puede tener apendicitis.** Con la regla anterior
—«toda exclusión exige `ref`»— el ejemplo insignia del propio motor de veredicto
no podría emitirse nunca. Es el precedente exacto de `no_medible`, que exige
`motivo` porque no hay cociente que citar. Y pone el freno donde hace falta:
`mecanismo` es el valor que **hay que justificar por escrito**, no la puerta
trasera por la que entra lo que carece de estudio.

#### Qué autoriza una bandera roja

**Autorizan `discriminacion_medida` y `consenso_con_afirmacion`.
`consenso_de_lista` NO.** `mecanismo` autoriza `excluye`.

El criterio es la **parsimonia: la explicación única supera a la múltiple.** Una
bandera roja empuja hacia la explicación múltiple —obliga a un apoyo extra, o
tumba el diagnóstico— y hacer eso sobre la mera pertenencia a una lista es
multiplicar hipótesis sin necesidad.

El argumento fino, que es el que decide: una fiebre en un paciente con síntomas
de intestino irritable **no contradice** el diagnóstico, simplemente no es de su
territorio. Obliga a explicar la fiebre, no a abandonar la hipótesis. Declararla
bandera roja afirma algo más fuerte —que argumenta *en contra*— y eso es
exactamente lo que ninguna reseña mide.

**La tensión, registrada.** Las banderas rojas de los criterios MDS son también
items de consenso: el panel las declara sin medirlas una por una, y son
contrarrestables precisamente porque ninguna decide sola. La postura contraria
es defendible. Lo que inclina la decisión es que MDS declara su lista **como
criterio**, con su nombre y su panel detrás, mientras que una reseña que enumera
síntomas de alarma no compromete a nadie a nada.

#### `nucleo` y `balance` — claves de la condición, no de la arista

Van al primer nivel porque no son propiedades de una arista sino precondiciones
sobre varias:

```yaml
nucleo:
  requiere: ['HM:xxxx']                      # todos
  y_al_menos_uno_de: ['HM:yyyy', 'HM:zzzz']  # al menos uno
  ref: 'pmid:26474316'

balance:
  ref: 'pmid:26474316'
  establecida: {apoyos_minimos: 2, banderas_maximas: 0}
  probable:    {contrapeso: 1, banderas_maximas: 2}
```

**`balance` exige `ref`.** Los enteros los fija el panel que redacta el
criterio; el sistema no los deriva.

#### `odds_ratio`, campo aparte

Nunca dentro de `lr_positivo` ni `lr_negativo`, y con las covariables
declaradas:

```yaml
odds_ratio: {valor: 2.7, ic95: [1.4, 5.1], ref: 'pmid:15082584',
             covariables: 'edad de inicio, sexo, criterios de Manning'}
```

Un OR de regresión logística depende de qué otras covariables entraron en el
modelo, así que **ni siquiera es una propiedad del hallazgo**. Si el motor
bayesiano pudiera leerlo por accidente, lo multiplicaría como si fuera un
cociente.

#### `graduacion` — cuando el cociente cambia con el valor

Un hallazgo de laboratorio no es binario. El índice ya guardaba eso en `tramos`,
pero la frontera del tramo vivía **solo en prosa** —«linfocitos atípicos ≥ 10%»,
«7 a 10 (riesgo alto)»—, y ningún consumidor puede leer eso: el valor volvía a
ser binario en cuanto salía de aquí. `graduacion` declara el eje y cada tramo
puede traer sus límites como números, **sin perder la prosa**, que sigue siendo
la etiqueta que imprime el libro.

```yaml
graduacion:
  parametro: Linfocitos atípicos    # qué se gradúa
  unidad: '%'                       # obligatoria en cuanto haya un número
  lectura: acumulativo              # acumulativo | disjunto
tramos:
  - {umbral: 'linfocitos atípicos ≥ 10%', desde: 10, lr_positivo: 11.4, ref: 'pmid:27115266'}
  - {umbral: 'linfocitos atípicos ≥ 20%', desde: 20, lr_positivo: 26,   ref: 'pmid:27115266'}
```

**`lectura` no se infiere.** Las dos formas se parecen en el YAML y dicen cosas
opuestas:

| `lectura` | Qué son los tramos | Cómo se lee un valor |
|---|---|---|
| `disjunto` | intervalos `[desde, hasta)` que no se solapan | cae en uno y sólo en uno |
| `acumulativo` | cortes de un solo lado, anidados a propósito | se aplica el **más estricto** que satisface |

La mononucleosis es el caso que obliga a distinguirlas: la fuente midió «≥ 10%»,
«≥ 20%» y «≥ 40%» sobre poblaciones que se contienen unas a otras. Partirlas en
`[10,20)` y `[20,40)` para que no se solapen **inventaría tres cocientes que
nadie midió**. Un validador que exigiera intervalos disjuntos siempre obligaría
a esa invención, así que la forma se declara.

**Los intervalos son semiabiertos, `[desde, hasta)`.** Omitir un extremo lo abre,
que es más honesto que escribir `desde: 0` afirmando un límite que nadie midió.
En una escala entera esto se ve raro y **no es una errata**: el estrato «7 a 10»
de HEART se escribe `desde: 7, hasta: 11`, porque el 10 tiene que entrar y el
extremo superior no entra nunca.

**Los tramos no tienen que cubrir toda la recta.** HEART declara `0–3` y `7–10`
porque la fuente no publica el cociente de `4–6`. Un valor que no cae en ningún
tramo significa que esta hipótesis no sabe leerlo, y eso se dice; rellenarlo por
interpolación sería inventar.

**Cada tramo cita su fuente**, como cualquier otro cociente. Un tramo sin `ref`
no entra: la regla dura no tiene excepción por ser un tramo.

##### Los dos ejes, que no son intercambiables

`umbral` gradúa **el hallazgo**: «≥ 10%» y «≥ 20%» son dos intensidades del mismo
signo. `umbral_condicion` redefine **la condición contra la que se mide**: en el
aneurisma, «≥ 3 cm» y «≥ 4 cm» son la misma palpación evaluada contra dos
diagnósticos distintos. El consumidor busca en el primero dónde cae el valor del
paciente; en el segundo elige según qué está preguntando. Mezclarlos en una
misma lista es un error de `build.py`.

##### Estratificación por edad o sexo

No es una clave nueva dentro del tramo: es **otra población medida**, y se
declara con `poblacion` en el tramo. El solapamiento se comprueba dentro de cada
población y no entre ellas, porque el corte de varón y el de mujer se solapan por
definición. `poblacion` sigue siendo prosa, como en el resto del índice, así que
un consumidor que no sepa a qué población pertenece su paciente tiene que decirlo
en vez de elegir un tramo.

##### `lr_negativo` junto a tramos graduados

Tiene que declarar `umbral` o `umbral_condicion`. Un LR− suelto no dice a qué
corte llama «negativo», y ése es justo el número con el que se descarta.

##### Unidades

La unidad canónica vive en el **concepto**, dentro de su `umbral`. Cuando el
concepto la declara, la `graduacion` de la arista la **comprueba** en vez de
volver a declararla, y la discrepancia se caza en `build.py`. Los múltiplos del
límite superior de normalidad (`xLSN`) y los valores absolutos conviven, y la
`unidad` distingue cuál es: **el índice no convierte entre ellos**, porque
hacerlo exige el LSN del laboratorio local, que el índice no conoce ni debe
conocer. Se guarda la escala en la que la fuente publicó el corte.

---

## 3. Convención de identificadores

Continúa la serie `HM:` del vocabulario semilla. **No se abre un espacio de
nombres paralelo.**

| Bloque | Contenido | Ocupado |
|---|---|---|
| `HM:0001` | raíz «Hallazgo clínico» | 1 |
| `HM:01xx`–`HM:09xx` | hallazgos por sistema | 117 |
| `HM:10xx` | trastornos (raíz y agrupación) | 3 |
| `HM:2000`–`HM:23xx` | procedimientos | 15 |
| **`HM:30xx`–`HM:59xx`** | **signos nuevos** | **74** de ~2900 |
| **`HM:60xx`–`HM:89xx`** | **condiciones (síndromes y enfermedades)** | **18** de ~3000 |

Los 74 del bloque nuevo no salieron del temario, pese al nombre que llevaba
antes esa fila: los acuñó una condición al necesitarlos. El temario sigue
íntegro y sin consumir.

Los códigos son **permanentes**: una vez publicados, otros sistemas los citan.
No se reutilizan ni se renumeran.

El bloque de condiciones se amplió de `79xx` a `89xx` antes de acuñar el primero:
el temario aporta ~510 condiciones y el rango anterior dejaba poco margen para
crecer con orden. Ampliar es gratis antes del primer código e imposible después.

### Condiciones acuñadas

| Código | Condición | Aristas con cociente | Fuente |
|---|---|---|---|
| `HM:6001` | Hepatitis viral aguda | 0 | — |
| `HM:6002` | Síndrome de intestino irritable | 0 | — |
| `HM:6003` | Mononucleosis infecciosa | 6 | `pmid:27115266` |
| `HM:6004` | Meningitis aguda | 1 | `pmid:10411200` |
| `HM:6005` | Derrame pleural exudativo | 4 | `pmid:24938565` |
| `HM:6006` | Aneurisma de aorta abdominal | 1 (2 tramos) | `pmid:9892455` |
| `HM:6007` | Síndrome coronario agudo | 5 + 3 escalas | `pmid:26547467` |
| `HM:6008` | Hipovolemia | 3 | `pmid:10086438` |
| `HM:6009` | Faringitis estreptocócica | 5 | `pmid:11147989` |
| `HM:6010` | Síncope cardíaco | 9 + 1 escala | `pmid:31237649` |
| `HM:6011` | Infección precoz por VIH | 6 | `pmid:25027143` |
| `HM:6012` | Artrosis de cadera | 8 | `pmid:31846019` |
| `HM:6013` | Enfermedad del manguito rotador | 2 | `pmid:23982370` |
| `HM:6014` | Rotura completa del manguito rotador | 2 | `pmid:23982370` |
| `HM:6015` | Enfermedad de Parkinson | 0 (`nucleo` + `balance`) | `pmid:26474316` |
| `HM:6016` | Embarazo ectópico | 5 | `pmid:23613077` |
| `HM:6017` | Conjuntivitis bacteriana | 2 | `pmid:35699701` |
| `HM:6018` | Apnea obstructiva del sueño | 2 | `pmid:23989984` |
| `HM:6019` | Luxación de cadera en el lactante | 3 | `pmid:38619828` |
| `HM:6020` | Intubación difícil | 5 | `pmid:30721300` |
| `HM:6021` | Trastorno por consumo de alcohol | 5 | `pmid:38592385` |
| `HM:6022` | Glaucoma primario de ángulo abierto | 4 | `pmid:23677315` |
| `HM:6023` | Conmoción cerebral pediátrica | 8 | `pmid:41941197` |
| `HM:6024` | Maltrato físico infantil | 7 | `pmid:40257808` |
| `HM:6025` | Hipertensión arterial secundaria pediátrica | 7 | `pmid:36976276` |
| `HM:6026` | Insuficiencia aórtica | 3 | `pmid:10376577` |
| `HM:6027` | Rotura del ligamento cruzado anterior | 3 | `pmid:11585485` |
| `HM:6028` | Alergia a penicilina | 2 | `pmid:11368703` |
| `HM:6029` | Hipertensión arterial en adultos | 2 | `pmid:34313682` |
| `HM:6030` | Infarto agudo de miocardio | 9 | `pmid:9786377` |
| `HM:6031` | Trastorno de ansiedad generalizada | 1 | `pmid:25058220` |
| `HM:6032` | Trastorno de pánico | 1 | `pmid:25058220` |
| `HM:6033` | Melanoma cutáneo | 3 | `pmid:9496989` |
| `HM:6034` | Cáncer de mama | 2 | `pmid:10517431` |

La columna cuenta **aristas**, no cocientes: el aneurisma tiene una sola arista
—la palpación— y trae cuatro cifras, porque cada tramo de diámetro la mide
contra una condición distinta.

Las dos primeras se acuñaron al publicarse sus páginas en medsemiotics y **no
figuran en el temario**: se publicaron por delante de él. Es el patrón ya
observado en gastroenterología —faltan también cirrosis, colitis ulcerosa,
pancreatitis y *H. pylori*—, y confirma que el temario es hoja de ruta parcial,
no censo de lo que debe existir.

Las doce siguientes (`HM:6003`–`HM:6014`) se eligieron al revés: por tener
cociente publicado y verificable en la serie *Rational Clinical Examination*.
Ese criterio tiene un límite conocido —la serie anterior a 1999 no tiene
abstract en PubMed, así que ascitis y esplenomegalia quedaron fuera pese a ser
signos ya publicados en biosemiotics—.

`HM:6015` entró por otra razón y rompe el patrón a propósito: no aporta ningún
cociente, sino la estructura de `nucleo` y `balance` que ninguna condición
anterior necesitaba. `HM:6016` retoma la veta donde la había dejado `HM:6014`.

---

## 4. Estado actual — qué hay y de dónde sale

### Fuentes disponibles

| Fuente | Aporta | Cantidad | Estado |
|---|---|---|---|
| `vocabulario_semilla.json` de holonmed | esqueleto de IDs, sinónimos, jerarquía | **136 conceptos** | ✅ sembrado |
| `refs.bib` de biosemiotics | referencias con PMID + DOI | **74** | ✅ convertido y verificado |
| Serie *Rational Clinical Examination* | revisiones con cociente publicado | **14 fuentes** | ✅ 61 aristas medidas |
| 14 signos de biosemiotics | significante, significado, umbral, falsos positivos | **14** | listo, requiere normalizar |
| 14 conceptos de biosemiotics | física y artefactos, grafo de prerrequisitos | **14** | listo |
| Skills de holonmed | aristas con LR y fuente | **7 aristas** | pendiente (oleada 1) |
| Skills de holonmed | parámetros de laboratorio con corte | **19** únicos | ✅ incrustados en su concepto |
| Temario DeGowin | términos con tipo SIGN/SYNDROME/DISEASE | **1113** | 991 limpios · 122 a revisar |

### El temario completo está versionado

Los **1113 términos** no viven en este documento: viven en
[`datos/temario.csv`](datos/temario.csv), con su tipo, su estado, el motivo de
revisión y las variantes que se fusionaron. El cruce contra el vocabulario
semilla está en [`datos/casamiento.csv`](datos/casamiento.csv), también con las
1113 filas y una columna `decision` en blanco para confirmarlas a mano.

Ninguno de los dos se toca al avanzar por oleadas. La oleada en curso consume el
temario, no lo consume ni lo reduce: el listado completo sigue ahí desde el
primer día hasta el último. Ver [`datos/README.md`](datos/README.md).

### Cobertura por capa

| Capa | Poblado | Falta |
|---|---|---|
| **Referencias** | 112 | las que traiga cada condición nueva |
| **Conceptos** | 279 | ~420 signos del temario |
| **Condiciones** | 34 | ~480 síndromes y enfermedades |
| **Aristas con cociente** | **122** | prácticamente todo |

**El cuello de botella sigue siendo la última fila.** Es la capa que da sentido
al índice —el consejo del experto que mueve la probabilidad— y la única que no
se siembra: se escribe, una arista cada vez, leyendo literatura.

Treinta y cuatro condiciones han costado treinta y tres fuentes verificadas. A ese ritmo,
las ~500 que faltan no son un sprint sino el trabajo de fondo del proyecto.

---

## 5. Oleadas de población

### OLEADA 0 — cimientos ✅ *completada*

- [x] **74 referencias** desde `refs.bib`, con PMID y DOI verificados
- [x] **136 conceptos** desde el vocabulario semilla
- [x] **19 umbrales de laboratorio** desde las skills de holonmed

Salieron 19 y no 21: la amilasa y la lipasa aparecían en dos skills distintas.
Los umbrales no viven en un directorio propio sino dentro del concepto que
definen, porque un punto de corte es propiedad del hallazgo, no una entidad.

### OLEADA 1.5 — condiciones con cociente publicado *(en curso, fuera de orden)*

Se adelantó a la oleada 1 por oportunidad: las revisiones sistemáticas de la
serie *Rational Clinical Examination* con abstract en PubMed son una veta
acotada y verificable, y convenía agotarla mientras estaba localizada.

- [x] 31 condiciones con **122 aristas medidas** (143 valores de LR) sobre 29 fuentes de la serie
- [x] osteoartritis de cadera → `HM:6012`, con 8 aristas de `pmid:31846019`
- [x] embarazo ectópico → `HM:6016`, con 5 aristas de `pmid:23613077`
- [x] conjuntivitis bacteriana → `HM:6017`, con 2 aristas de `pmid:35699701`.
- [x] apnea obstructiva del sueño → `HM:6018`, con 2 aristas de `pmid:23989984`.
- [x] neumonía infantil → `HM:6036`, con 6 aristas de `pmid:28763554`.
      **Desbloqueada el 06/09/2026 al cotejar su errata**: la corrección es suya,
      pero solo arregla un ejemplo ilustrativo de la sección Statistical Methods
      y una frase de los Key Points. Ningún cociente cambia. El cotejo casi sale
      al revés porque PMC sirve bajo ese DOI el cuerpo de otra corrección; hizo
      falta la página del editor.
- [x] luxación de cadera en el lactante → `HM:6019`, con 3 aristas de `pmid:38619828`.
- [x] intubación difícil → `HM:6020`, con 5 aristas de `pmid:30721300`.
- [x] trastorno por consumo de alcohol → `HM:6021`, con 5 aristas de `pmid:38592385`.
- [x] glaucoma primario de ángulo abierto → `HM:6022`, con 4 aristas de `pmid:23677315`.
- [x] conmoción cerebral pediátrica → `HM:6023`, con 8 aristas de `pmid:41941197`.
- [x] maltrato físico infantil → `HM:6024`, con 7 aristas de `pmid:40257808`.
- [x] hipertensión arterial secundaria pediátrica → `HM:6025`, con 7 aristas de `pmid:36976276`.
- [x] insuficiencia aórtica → `HM:6026`, con 3 aristas de `pmid:10376577`.
- [x] rotura del ligamento cruzado anterior → `HM:6027`, con 3 aristas de `pmid:11585485`.
- [x] alergia a penicilina → `HM:6028`, con 2 aristas de `pmid:11368703`.
- [x] hipertensión arterial en adultos → `HM:6029`, con 2 aristas de `pmid:34313682`.
- [x] infarto agudo de miocardio → `HM:6030`, con 9 aristas de `pmid:9786377`.
- [x] trastorno de ansiedad generalizada → `HM:6031`, con 1 arista de `pmid:25058220`.
- [x] trastorno de pánico → `HM:6032`, con 1 arista de `pmid:25058220`.
- [x] melanoma cutáneo → `HM:6033`, con 3 aristas de `pmid:9496989`.
- [x] cáncer de mama → `HM:6034`, con 2 aristas de `pmid:10517431`.
- [x] trombosis venosa profunda → `HM:6035`, con `pmid:16403932`. **Es la
      excepción de la serie**: la fuente no publica ningún cociente de signo ni
      de síntoma, así que la condición no tiene aristas de exploración. Lo que
      entra es el dímero D con seis cocientes negativos —cruce de tres estratos
      de probabilidad previa por dos clases de ensayo— y la prevalencia por
      estrato de la regla de predicción.
- [x] sobrecarga de volumen → `HM:6037`, con 8 aristas y **12 cocientes** de
      `pmid:41729549`. La fuente más rica de la serie. Seis conceptos nuevos
      (`HM:3146`-`HM:3151`), cinco de ellos con umbral y procedencia. Los
      valores son los del **abstract corregido en la página del editor**, no los
      del que sirve PubMed.
#### Qué queda de verdad (revisado el 06/09/2026 contra `referencias/`)

**La veta está agotada.** De las 112 referencias, 33 sostienen algún dato y 79
no; pero de esas 79 **solo quedaban 3 de la serie**, y las tres traían errata.
Las tres se cotejaron el 06/09/2026 y **dieron tres resultados distintos**;
modelada la sobrecarga de volumen, **ya no queda ninguna bloqueada por su
errata**. Lo que falta ahora es escribir aristas, no abrir puertas. Las otras 75
son
ecografía y cuidados críticos —*Intensive Care Med*, *J Am Soc Echocardiogr*, *Ultrasound
J*, *Radiographics*—: el fondo de biosemiotics que entró con `refs.bib`, y por
tanto material de la **oleada 1**, no de ésta.

Conviene no confundir dos cosas que esta sección mezclaba:

- **En el repositorio y sin modelar** — las 2 de abajo. En las dos el trabajo
  ya es solo leer el abstract y escribir las aristas.
- **Ni siquiera obtenidas** — abstinencia alcohólica grave, disfunción tiroidea,
  ascitis, esplenomegalia. **No están en `referencias/`**: hay que traerlas por
  PMID y verificarlas antes de que exista nada que modelar. Es otro trabajo y
  otra fase.

Las 2 de la serie que quedan sin modelar, con sus erratas ya cotejadas:

| Referencia | Año | Estado tras el cotejo del 06/09/2026 |
|---|---|---|
| `pmid:26717031` · neuroimagen en TCE leve del adulto | 2015 | **LISTA, y con un dato de regalo.** La corrección («Data Error») acota su alcance a una fila de la Tabla 1 y a una frase de los Resultados; el abstract no está afectado. Además aporta un cociente que el abstract no traía: GCS < 14 a las dos horas, LR 3.4 (IC95% 1.4-8.4). Nueve cocientes esperando |
| `pmid:26241601` · estrés postraumático | 2015 | **PARCIAL.** Solo entra el Trauma Screening Questionnaire, y sus cifras las da el propio aviso: Se 0.95, Sp 0.26, LR+ 1.3 (1.2-1.4), LR− 0.20 (0.10-0.41). **El abstract sigue bloqueado**: la corrección dice que retiró dos frases y redondeó valores, pero no dice cuáles. Para desbloquearlo hace falta el abstract corregido del artículo (`10.1001/jama.2015.7877`), como en la sobrecarga de volumen |

**Al cotejar una errata, empieza por localizarla**: tiene su propio PMID y a
menudo su propio PMC, aunque el artículo corregido esté de pago.

**Identifícala por su DOI, no por su página.** JAMA agrupa varias correcciones
en una misma página: la 90 del 315(1) lleva **tres**, cada una con su PMID y su
DOI. Buscar «la errata de la página 90» devuelve las tres y no dice cuál es.

**Y termina en la página del editor.** El cotejo de `pmid:28763554` casi sale al
revés: PMC sirve bajo el DOI correcto el cuerpo de OTRA corrección, con otro
título, que no menciona el artículo cotejado. Leer solo PMC llevaba a concluir
que la errata era ajena y el enlace espurio. No lo era: la corrección real
existía y estaba en jamanetwork. **Que el cuerpo hallado no mencione tu artículo
no prueba que la errata sea ajena; prueba que estás mirando el sitio
equivocado.**

**La aritmética orienta pero no autoriza, y su silencio no absuelve.** En
`pmid:26241601` el abstract da dos cocientes distintos para el mismo instrumento
y el mismo corte, y solo uno de los dos bloques cuadra con la sensibilidad y la
especificidad que él mismo declara —`LR+ = Se/(1−Sp)`—. Eso señala cuál es
probablemente el corregido, y no basta: quién corrige a quién lo dice el aviso.
**Leído el aviso, la aritmética sigue sin veredicto**: la corrección confirma
que sobraban dos frases, pero no dice cuál de los dos bloques retiró. Haber
esperado no fue prudencia excesiva; era la única lectura honesta.

El caso opuesto es `pmid:26717031`, cuyo abstract **sí** cuadra consigo mismo
—sus probabilidades postprueba se derivan bien de su prevalencia y sus
cocientes—. Eso no lo absolvía: un bloque de cifras uniformemente erróneo cuadra
consigo mismo igual de bien. **Que sume no significa que sea correcto.** El
aviso acabó dándole la razón al abstract, y la cautela seguía siendo correcta:
la conclusión benigna la trajo la corrección, no la aritmética.

**Estar en PMC no es tener el texto.** Dos de las tres correcciones tenían
depósito en PMC y las dos lo servían **vacío**: JAMA deposita el registro sin
cuerpo. Comprobar que existe el PMC no adelanta el cotejo; hay que abrir la
página del editor igual.

##### Lo que enseñaron los tres cotejos juntos

**Leer la corrección no siempre desbloquea.** Tres avisos que se parecían mucho
—misma revista, misma serie, los tres titulados como si tocaran datos— dieron
tres resultados: uno abrió la fuente entera, otro abrió una fila, el tercero la
dejó igual de cerrada.

**Lo que decide es si la corrección ACOTA su alcance.** «Data Error» nombra la
fila, la tabla y la frase, y con eso todo lo demás queda a salvo. «Incorrect
Data in Rational Clinical Examination Article» dice «in the abstract, text,
supplement, and video» y no enumera nada: confirma el daño sin delimitarlo, que
para quien transcribe es peor que no saber.

**Cuando no lo acota, lo que hace falta ya no es la corrección: es el artículo
corregido.** JAMA corrige en línea sobre el propio artículo. El abstract que
sirve PubMed puede ser el anterior —en `pmid:26241601` conserva las dos frases
que el aviso retiró, y en `pmid:41729549` sigue dando las doce cifras viejas—,
así que hay que ir al DOI del artículo, no al de la errata. Fue leer ese
abstract corregido, y no el aviso, lo que desbloqueó la sobrecarga de volumen.

**La aritmética acierta la fila y falla la reparación.** Es el hallazgo más útil
de los tres cotejos y conviene que quede escrito con su número. En
`pmid:41729549` la comprobación cruzada señalaba el BNP como la única fila cuya
especificidad declarada (87%) no cuadraba con la derivada (93%). **Acertó**: de
los doce cocientes, el BNP fue el que más movió la corrección, de LR+ 6.9 a 4.2.
Pero los valores que la aritmética implicaba eran Se 90% y Sp 93%, **y los
corregidos son Se 93% y Sp 78%**. Haber «arreglado» la fila con la aritmética
habría dejado la especificidad más lejos de la verdad que el error original.

La razón es simple y hay que tenerla presente: la comprobación cruzada detecta
que una fila es incoherente, pero no puede decir **cuál** de sus cuatro cifras
lo es. Sirve para saber dónde mirar. Nunca para escribir.

**Y una corrección puede volver un hallazgo indistinguible del ruido.** En
`pmid:41729549` los crepitantes pasan de LR 2.7 (IC95% 1.7-4.5) a 2.7
(IC95% **0.7**-4.5): el valor puntual no se mueve y el intervalo pasa a cruzar
el 1. Un consumidor que solo lea el valor puntual no notará nada. Se transcribe
tal cual, con su advertencia, porque recortar el intervalo para que «tenga
sentido» sería inventar.

**Una corrección puede mover el umbral y el cociente a la vez.** En
`pmid:26717031`, «GCS < 15 a las 2 h, LR 1.6-7.6» pasó a «GCS < 14 a las 2 h, LR
3.4 (1.4-8.4)». Con el corte viejo el número no queda impreciso: queda siendo el
de otro hallazgo. Es la justificación más limpia que tiene la regla de no
transcribir nunca un cociente sin su umbral.

**«No altera los resultados ni las conclusiones» no es un salvoconducto.** Lo
dice el aviso de `pmid:41729549`, y habla de las conclusiones del artículo, no
de cada cifra: un cociente puede cambiar sin mover la conclusión de que el BNP
es la mejor prueba aislada. Aquí se transcriben cifras.

**Y `errata_verificada` no se pone por haber leído.** Se pone cuando la lectura
autoriza a transcribir. En `pmid:41729549` el cotejo está hecho y el campo sigue
sin poner a propósito, para que `build.py` convierta en error cualquier intento
de citarla. El campo dice «esta cifra está cotejada», no «alguien miró».

#### Pendientes declarados dentro de las condiciones

No viven en este mapa sino en la clave `pendiente` de cada registro, que es donde
se ven al trabajar. Hoy son nueve. La mayoría espera **texto completo**: las tres
reglas de predicción de la faringitis (`HM:6009`), la resistencia a la rotación
externa del manguito (`HM:6013`), los biomarcadores del síncope (`HM:6010`).

Dos son decisiones de esquema y no de literatura:

- `HM:6018` — la fuente publica «ronquido leve **y** IMC < 26» con LR− 0.07. Es
  un cociente de dos hallazgos combinados, y el esquema no tiene sitio para eso:
  no es una arista ni una `regla`.
- `HM:6015` — los criterios de apoyo de MDS piden `consenso_con_afirmacion` y no
  `consenso_de_lista`, y esa distinción hay que justificarla por escrito.

Y uno que **ya tiene solución**: `HM:6016` deja fuera la hCG diciendo que entrará
«probablemente como tramos y no como cifra suelta». Ese mecanismo existe desde
que se acuñó `graduacion`.

- [ ] pendiente aparte, y sigue abierto: el extremo del rango 7.1–250 del
      colesterol pleural (`HM:3008`), que exige el texto completo

### OLEADA 1 — lo que ya está escrito y revisado
Migrar lo que biosemiotics y holonmed tienen validado.

- [ ] **14 signos** de biosemiotics con su tríada completa
- [ ] **14 conceptos** base con `se_basa_en` y `contrasta_con`
- [ ] **1 condición** (pancreatitis aguda) con sus **7 aristas** y sus fuentes

Al cerrar esta oleada, el índice ya sirve a los tres clientes y se puede
invertir la dirección con biosemiotics.

### OLEADA 2 — el temario limpio
Los 991 términos que pasaron la normalización, por tipo.

- [ ] **96 enfermedades** — el bloque más limpio (91% sin marcas de corte)
- [ ] **419 síndromes** — 359 limpios
- [ ] **598 signos** — 544 limpios

Entran **sin LR**, con `estado_lr: no_medido`. Poblar identidad y sinónimos
primero; las aristas vienen después y de una en una.

### OLEADA 3 — las aristas
El trabajo real y el que no se puede automatizar: cada LR con su población, su
intervalo de confianza y su PMID.

Prioridad por rendimiento clínico, no alfabética: primero las condiciones que
holonmed ya sabe triar, después las de mayor frecuencia en primer contacto.

### PENDIENTE — los 122 a revisar
Los términos con marcas de corte del extractor. Se reparan a mano; no se
adivinan. Ver `temario.csv`, columna `estado=revisar`.

---

## 6. Orden de trabajo recomendado

1. **Referencias** — hecho. No depende de nada y desbloquea las fuentes de todo.
2. **Conceptos desde la semilla** — fija el espacio de IDs antes de que nadie
   acuñe uno nuevo.
3. **Casar el temario contra la semilla** — cuántos de los 1113 ya existen como
   `HM:` y cuántos son nuevos. Sin este paso se crean duplicados.
4. **Migrar biosemiotics** — en un solo PR con el cambio de sus validadores.
5. **Condiciones y aristas** — de una en una, con revisión.

### La regla que no cambia

**Ningún LR entra sin `ref` resoluble.** Un cociente sin procedencia es un
número inventado con formato científico, y mueve la probabilidad que ve un
clínico. Es la regla que biosemiotics aplica a las citas y holonmed a las
fuentes; aquí se aplica a las dos cosas a la vez.

**PubMed es autoridad para título, año y retractación. CrossRef solo confirma
que el DOI resuelve.** Comprobado sobre las 74: cuatro títulos de CrossRef están
truncados o con erratas —una de ellas dice «Critically III» desde 1995—.
Comparar títulos contra CrossRef genera falsas alarmas.

---

## 7. Conteo

```
                        hoy      al cerrar oleada 2
referencias             112             112
conceptos               281            ~800
condiciones              36            ~515
aristas con cociente    128             128
```

Lo que este mapa deja claro: **sembrar es barato, medir es caro.** Las tres
primeras filas se llenan copiando y normalizando. La cuarta se llena leyendo
literatura, una arista cada vez, y es la única que no se puede acelerar.

---

## 8. Decisiones abiertas

- **Licencia del vocabulario semilla.** Hoy declara `AGPL-3.0-or-later`. Para
  entrar en un índice CC0 hay que relicenciarlo explícitamente. Es obra propia,
  así que basta la decisión, pero tiene que constar.
- **Identificador canónico de las referencias.** Hoy `pmid:`. Si el índice debe
  admitir guías, libros y documentos de sociedades —que CrossRef sí cubre—,
  hace falta un identificador propio para lo que no tiene PMID.

**Resuelto el 20/08/2026 — el DOI no es obligatorio.** `build.py` exige `id`,
`titulo`, `identificadores` y `verificacion`; el DOI nunca estuvo entre ellos.
Que las 88 primeras referencias lo tuvieran era casualidad, no regla. Holten
2003 (`pmid:12776965`) entra sin DOI porque PubMed no le asigna ninguno, con
`doi: null` y la nota de por qué. El eje `efecto` ya no está en esta sección:
se documentó en la §2 el mismo día.
- **Directorio de referencias plano o por año.** 74 en plano funciona; a partir
  de unos miles conviene particionar.

**Resuelto el 06/09/2026 — las bandas de LR, respondiendo a la propuesta de
holonmed.** El eje entra como `graduacion` + límites en los `tramos` que el
índice ya tenía, y no como una clave `bandas` nueva. Las cuatro preguntas
abiertas de la propuesta se resuelven así:

1. **`analito` no entra.** Aquí la identidad de un signo es su código `HM:`, que
   es permanente y es lo que citan los tres clientes. Un nombre de analito en
   texto libre reintroduciría la identidad-por-nombre que los códigos existen
   para evitar; `graduacion.parametro` describe, no identifica.
2. **Unidades canónicas: sí, en el concepto.** `umbral.unidad` es la
   declaración; la arista comprueba. **Cerrado el 06/09/2026: los 25 conceptos
   con umbral traen unidad**, y el aviso `umbral sin unidad` ya no señala a
   ninguno.

   **El criterio**, que es lo que sobrevive al caso, no es escribir la unidad más
   común: es escribir la que hace coherente **el corte que ya está escrito**.
   38.0 solo es fiebre en °C, 12.0 de hemoglobina solo existe en g/dL, 11000
   leucocitos solo se cuentan por µL —en cada caso la alternativa daría un número
   distinto en un orden de magnitud, así que el dato presente determina la unidad
   y no queda nada que elegir—. Así entraron 19 de los 20 heredados, en el #10.

   Cuando el corte **no** la determina, no se adivina: un corte de 10 de proteína
   C reactiva es plausible en mg/L y en mg/dL, y las dos lecturas se diferencian
   en un factor de 10, que es justo el error que la unidad existe para impedir.
   `HM:0761` esperó por eso, y lo resolvió **el responsable clínico**, que es de
   quien depende esa decisión: `mg/L`.

   **La unidad no es la procedencia.** `HM:0761` sigue sin `ref`, como los otros
   19: la unidad dice en qué escala está el 10, no de dónde sale el 10. Los 20
   avisos `umbral sin procedencia` siguen intactos.
3. **`xLSN` y valor absoluto conviven**, y `unidad` distingue cuál es. El índice
   no convierte entre ellos.
4. **Edad y sexo entran ya, sin v2**, como `poblacion` del tramo — que es lo que
   son: otra población medida, no otra clave dentro de la banda.

Dos cosas que la propuesta no contemplaba y que el índice sí necesita:
`lectura`, porque los cortes acumulativos de la mononucleosis no se pueden
expresar como intervalos disjuntos sin inventar cocientes; y la separación entre
`umbral` y `umbral_condicion`, que ya estaba en los datos y que una clave
`bandas` única habría aplanado.
