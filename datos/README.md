# datos/

Hojas de trabajo pendientes de revisión humana. No son registros del índice:
son el material del que saldrán.

## `temario.csv`

1113 términos con su tipo (`SIGN` / `SYNDROME` / `DISEASE`), extraídos de la
taxonomía de partida. Solo términos: ninguna definición del original.

**Este archivo es ahora la fuente, no una copia.** El `.jsonl` del que salió se
eliminó en agosto de 2026 por sus derechos de autor, así que el temario no se
puede regenerar ni cotejar contra el original. Los 122 términos marcados para
revisar se reparan con criterio clínico, no volviendo a la fuente.

- `estado = ok` — 991 términos limpios
- `estado = revisar` — 122 con marcas de corte del extractor

Los de `revisar` **se reparan contra la fuente, no se adivinan**. La columna
`motivo` dice qué se detectó y `variantes` qué formas se fusionaron.

## `casamiento.csv`

Propuesta de correspondencia entre el temario y los 136 conceptos sembrados.
La columna `decision` está vacía a propósito: se rellena a mano.

| confianza | filas | qué hacer |
|---|---|---|
| `alta` | 10 | confirmar; son cognados exactos |
| `media` | 5 | revisar una a una |
| `ninguna` | 1098 | necesitan código nuevo |

El solapamiento real ronda el 2%, y no es un fallo del método: los dos
vocabularios se construyeron para cosas distintas. La semilla cubre atención
aguda —signos vitales, dolor, laboratorio—; el temario cubre semiología y
enfermedades con nombre propio. Se complementan casi sin pisarse.

**Dos filas que no deben confirmarse tal cual:**

- `Hyperthermia → HM:0101 Fiebre` aparece como alta y **no son lo mismo**: la
  hipertermia es fallo de la termorregulación; la fiebre conserva el control
  hipotalámico. Necesita concepto propio.
- `Abdominal → HM:2302 Tomografía abdominal` es un falso positivo: casa un
  adjetivo truncado contra un procedimiento.
