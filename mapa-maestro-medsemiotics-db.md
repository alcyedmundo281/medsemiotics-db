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
`medido` · `no_medido` · `sin_efecto`

La distinción no es cosmética: *no medido* y *medido con LR 1.0* son cosas
distintas, y holonmed necesita saber si ignorar la arista o tratarla como
neutra.

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
| **`HM:30xx`–`HM:59xx`** | **libre: signos nuevos del temario** | 0 de ~2900 |
| **`HM:60xx`–`HM:79xx`** | **libre: condiciones (síndromes y enfermedades)** | 0 de ~2000 |

Los códigos son **permanentes**: una vez publicados, otros sistemas los citan.
No se reutilizan ni se renumeran.

---

## 4. Estado actual — qué hay y de dónde sale

### Fuentes disponibles

| Fuente | Aporta | Cantidad | Estado |
|---|---|---|---|
| `vocabulario_semilla.json` de holonmed | esqueleto de IDs, sinónimos, jerarquía | **136 conceptos** | listo |
| `refs.bib` de biosemiotics | referencias con PMID + DOI | **74** | ✅ convertido y verificado |
| 14 signos de biosemiotics | significante, significado, umbral, falsos positivos | **14** | listo, requiere normalizar |
| 14 conceptos de biosemiotics | física y artefactos, grafo de prerrequisitos | **14** | listo |
| Skills de holonmed | aristas con LR y fuente | **7 aristas** | listo |
| Skills de holonmed | parámetros de laboratorio con corte | **21** | listo |
| Temario DeGowin | términos con tipo SIGN/SYNDROME/DISEASE | **1113** | 991 limpios · 122 a revisar |

### Cobertura por capa

| Capa | Poblado | Fuente | Falta |
|---|---|---|---|
| **Referencias** | 74 | biosemiotics | — |
| **Conceptos** | ~150 | semilla + biosemiotics | ~450 signos del temario |
| **Condiciones** | 1 | holonmed | ~514 síndromes y enfermedades |
| **Aristas con LR** | **7** | holonmed | prácticamente todo |

**El cuello de botella está a la vista: hay 7 aristas con LR.** Es la capa que
da sentido al índice —el consejo del experto que mueve la probabilidad— y la
que menos material heredado tiene. Todo lo demás se siembra; esto se escribe.

---

## 5. Oleadas de población

### OLEADA 0 — cimientos *(sin decisiones pendientes)*
Se puede hacer hoy, no depende de nada.

- [x] **74 referencias** desde `refs.bib`, con PMID y DOI verificados
- [ ] **136 conceptos** desde el vocabulario semilla
- [ ] **21 parámetros de laboratorio** desde las skills de holonmed

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
