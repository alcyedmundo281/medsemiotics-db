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

---

## 3. Convención de identificadores

Continúa la serie `HM:` del vocabulario semilla. **No se abre un espacio de
nombres paralelo.**

| Bloque | Contenido | Ocupado |
|---|---|---|
| `HM:0001` | raíz «Hallazgo clínico» | 1 |
| `HM:01xx`–`HM:09xx` | hallazgos por sistema | 118 |
| `HM:10xx` | trastornos (raíz y agrupación) | 3 |
| `HM:2000`–`HM:23xx` | procedimientos | 15 |
| **`HM:30xx`–`HM:59xx`** | **signos nuevos del temario** | **30** de ~2900 |
| **`HM:60xx`–`HM:89xx`** | **condiciones (síndromes y enfermedades)** | **9** de ~3000 |

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
| `HM:6006` | Aneurisma de aorta abdominal | 2 | `pmid:9892455` |
| `HM:6007` | Síndrome coronario agudo | 5 + 3 escalas | `pmid:26547467` |
| `HM:6008` | Hipovolemia | 3 | `pmid:10086438` |
| `HM:6009` | Faringitis estreptocócica | 6 | `pmid:11147989` |

Las dos primeras se acuñaron al publicarse sus páginas en medsemiotics y **no
figuran en el temario**: se publicaron por delante de él. Es el patrón ya
observado en gastroenterología —faltan también cirrosis, colitis ulcerosa,
pancreatitis y *H. pylori*—, y confirma que el temario es hoja de ruta parcial,
no censo de lo que debe existir.

Las siete restantes se eligieron al revés: por tener cociente publicado y
verificable. Ese criterio tiene un límite conocido —la serie *Rational Clinical
Examination* anterior a 1999 no tiene abstract en PubMed, así que ascitis y
esplenomegalia quedaron fuera pese a ser signos ya publicados en biosemiotics—.

---

## 4. Estado actual — qué hay y de dónde sale

### Fuentes disponibles

| Fuente | Aporta | Cantidad | Estado |
|---|---|---|---|
| `vocabulario_semilla.json` de holonmed | esqueleto de IDs, sinónimos, jerarquía | **136 conceptos** | ✅ sembrado |
| `refs.bib` de biosemiotics | referencias con PMID + DOI | **74** | ✅ convertido y verificado |
| Serie *Rational Clinical Examination* | revisiones con cociente publicado | **7 fuentes** | ✅ 25 aristas medidas |
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
| **Referencias** | 81 | las que traiga cada condición nueva |
| **Conceptos** | 166 | ~450 signos del temario |
| **Condiciones** | 9 | ~505 síndromes y enfermedades |
| **Aristas con cociente** | **25** | prácticamente todo |

**El cuello de botella sigue siendo la última fila.** Es la capa que da sentido
al índice —el consejo del experto que mueve la probabilidad— y la única que no
se siembra: se escribe, una arista cada vez, leyendo literatura.

Nueve condiciones han costado nueve fuentes verificadas. A ese ritmo, las ~505
que faltan no son un sprint sino el trabajo de fondo del proyecto.

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

- [x] 7 condiciones con **27 aristas medidas** y 8 referencias nuevas
- [ ] resto de la serie sin revisar: apnea del sueño, embarazo ectópico,
      disfunción tiroidea, osteoartritis de cadera, consumo de alcohol
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
referencias              74              74
conceptos               ~150            ~750
condiciones               1             ~515
aristas con LR            7               7
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
- **Directorio de referencias plano o por año.** 74 en plano funciona; a partir
  de unos miles conviene particionar.
