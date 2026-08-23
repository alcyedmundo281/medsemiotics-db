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
| **Referencias** | 97 | las que traiga cada condición nueva |
| **Conceptos** | 210 | ~450 signos del temario |
| **Condiciones** | 18 | ~500 síndromes y enfermedades |
| **Aristas con cociente** | **61** | prácticamente todo |

**El cuello de botella sigue siendo la última fila.** Es la capa que da sentido
al índice —el consejo del experto que mueve la probabilidad— y la única que no
se siembra: se escribe, una arista cada vez, leyendo literatura.

Dieciocho condiciones han costado diecisiete fuentes verificadas. A ese ritmo,
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

- [x] 15 condiciones con **61 aristas medidas** sobre 14 fuentes de la serie
- [x] osteoartritis de cadera → `HM:6012`, con 8 aristas de `pmid:31846019`
- [x] embarazo ectópico → `HM:6016`, con 5 aristas de `pmid:23613077`
- [x] conjuntivitis bacteriana → `HM:6017`, con 2 aristas de `pmid:35699701`.
      La fuente compara viral contra bacteriana, no enfermedad contra salud:
      solo se emiten los cocientes que el abstract da a favor de bacteriana
      (secreción mucopurulenta, otitis media). Los que da a favor de viral
      (faringitis, adenopatía preauricular, contacto con ojo rojo) no se
      invierten —esa aritmética no la sostiene el abstract— y quedan
      declarados en `pendiente` para una futura «Conjuntivitis viral»
- [x] apnea obstructiva del sueño → `HM:6018`, con 2 aristas de
      `pmid:23989984`. La fuente publica además un cociente combinado
      («ronquido leve + IMC <26», LR− 0.07) que no se activa: `reglas` está
      pensado para criterios con nombre propio pendientes de decisión
      (cuántos componentes exigir), no para una combinación de dos hallazgos
      con cociente ya publicado. Queda en `pendiente` hasta que el esquema
      tenga un lugar propio para cocientes combinados de dos conceptos
- [!] **neumonía infantil descartada por ahora**: `pmid:28763554` (JAMA 2017,
      la revisión vigente) tiene una errata —«Incorrect Statistical Measures
      and Typographical Errors»— cuyo texto completo está bloqueado tanto en
      JAMA (403) como en PMC (`PMC12507477` no permite descarga del XML
      completo, solo metadatos). No se puede confirmar si las cifras del
      abstract sobreviven a la corrección, así que no se cita. La referencia
      queda creada (`referencias/pmid-28763554.yaml`) para que quien consiga
      leer la corrección complete esto sin repetir la búsqueda
- [ ] resto de la serie sin revisar. La búsqueda `"rational clinical
      examination"[Title] AND JAMA[Journal]` devuelve **59 registros**, así que
      la veta es bastante más ancha de lo que decía la lista anterior. Entre los
      revisados con cociente extraíble del abstract: glaucoma de ángulo
      abierto, luxación de cadera del lactante, intubación difícil, conmoción
      infantil, maltrato físico infantil, hipertensión secundaria del niño,
      síndrome de abstinencia alcohólica grave y trastorno por consumo de
      alcohol. Quedan fuera por medir escalas y no signos: ansiedad y pánico,
      obstrucción del tracto urinario inferior, mal de altura. Sin revisar
      todavía, la disfunción tiroidea y el grueso de la serie anterior a 2013
- [ ] pendientes de **texto completo**: ascitis y esplenomegalia (sin abstract),
      las tres reglas de predicción de la faringitis, y el extremo del rango
      7.1–250 del colesterol pleural

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
referencias              97              97
conceptos               210            ~800
condiciones              18             ~515
aristas con cociente     61              61
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
