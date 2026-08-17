# scripts/

Cómo se derivó cada registro del índice. **Versionados a propósito:** sin ellos
el contenido sería un volcado sin procedencia, imposible de auditar o rehacer.

`build.py` es el único que se ejecuta a diario. Los numerados son los pasos de
poblado; se corren cuando entra material nuevo.

## Fuentes externas

Viven fuera de este repositorio a propósito —aquí solo se versiona lo derivado—
y se indican por variable de entorno. Si falta una, el script se detiene con un
mensaje que la nombra.

| Variable | Qué es | De dónde sale |
|---|---|---|
| `BIOSEMIOTICS_REFS` | `refs.bib` | repo `biosemiotics` |
| `HOLONMED_VOCABULARIO` | `vocabulario_semilla.json` | repo `holonmed`, `backend/data/` |
| `HOLONMED_SKILLS` | directorio de protocolos `.md` | repo `holonmed`, `backend/skills/` |
| `TAXONOMIA_JSONL` | taxonomía de partida, con `term` y `type` | **ya no existe** — ver abajo |

> **El archivo de origen se eliminó en agosto de 2026**, por decisión del autor y
> por sus derechos. `3_temario_desde_taxonomia.py` se conserva porque documenta
> cómo se obtuvo `datos/temario.csv`, pero **no puede volver a ejecutarse**. El
> temario es ya la fuente: si un término necesita corrección, se corrige ahí.

**De `TAXONOMIA_JSONL` solo se leían los campos `term` y `type`.** Las
definiciones son texto de un manual con derechos y no se copian, no se derivan y
no entran en ningún registro. Un listado de nombres de enfermedades no es
material protegible; su texto sí.

## Los pasos

### `build.py` — valida
```bash
python scripts/build.py
```
Comprueba taxonomías, ids duplicados, padres colgados, aristas que apuntan a
conceptos inexistentes y —la regla que más importa— que **ningún LR carezca de
`ref` resoluble**. Sale con código 1 si hay errores. No modifica nada.

### `1_referencias_desde_bibtex.py` — siembra `referencias/`
```bash
BIOSEMIOTICS_REFS=/ruta/biosemiotics/refs.bib python scripts/1_referencias_desde_bibtex.py
```
Convierte el BibTeX en un registro por referencia y contrasta cada PMID contra
PubMed: título, año y estado de retractación. Conserva la `clave_bibtex`
original, que es la que citan hoy las fichas de biosemiotics.

### `2_verificar_crossref.py` — segunda verificación
```bash
python scripts/2_verificar_crossref.py
```
Resuelve cada DOI en CrossRef y anota el resultado.

**PubMed manda sobre CrossRef.** En la primera pasada, cuatro títulos de
CrossRef resultaron truncados o con erratas —uno dice «Critically III» desde
1995—. CrossRef sirve para confirmar que el DOI resuelve, no para validar
metadatos: comparar títulos contra él genera falsas alarmas.

### `3_temario_desde_taxonomia.py` — extrae el temario
```bash
TAXONOMIA_JSONL=/ruta/taxonomia.jsonl python scripts/3_temario_desde_taxonomia.py
```
Normaliza los términos, fusiona variantes de puntuación y plural, y marca los
que llevan marcas de corte del extractor. Produce `datos/temario.csv`.

**No fusiona por «syndrome» ni «disease»**: *Cushing Syndrome* y *Cushing
Disease* son entidades distintas.

### `4_sembrar_conceptos.py` — siembra `conceptos/`
```bash
HOLONMED_VOCABULARIO=/ruta/vocabulario_semilla.json \
HOLONMED_SKILLS=/ruta/holonmed/backend/skills \
python scripts/4_sembrar_conceptos.py
```
Genera un concepto por término del vocabulario semilla, con su jerarquía y sus
sinónimos, e incrusta los umbrales de laboratorio en el concepto que definen.

**Sobrescribe `conceptos/` y `referencias/` por completo.** Se ejecuta para
resembrar, no para actualizar: si has editado un registro a mano, revisa el diff
antes de commitear.

### `5_casar_temario.py` — cruza temario y semilla
```bash
HOLONMED_VOCABULARIO=/ruta/vocabulario_semilla.json python scripts/5_casar_temario.py
```
Empareja por cognados grecolatinos y produce `datos/casamiento.csv` con un nivel
de confianza por fila.

**No fusiona nada.** El emparejamiento automático de vocabularios clínicos en
dos idiomas produce falsos positivos peligrosos, así que cada propuesta se
confirma a mano en la columna `decision`. Incluye guardas que bloquean pares que
un motor de similitud confunde y un clínico jamás: `lipasemia`/`lipemia`,
`natremia`/`potasemia`, `hiper`/`hipo`.

## Orden

```
1 → 2        referencias verificadas
3            temario extraído
4            conceptos sembrados
5            casamiento propuesto  →  revisión humana  →  acuñar códigos nuevos
```

`build.py` después de cualquiera de ellos.
