# Respuesta a la propuesta de bandas de LR de holonmed

**Para**: holonmed, que consume este índice.
**De**: quien mantiene el índice.
**Fecha**: 06/09/2026.
**Estado**: acordado e implementado (PR #9 y #10, en `main`).

> **Este documento no es normativo.** Es el registro fechado de una respuesta.
> La especificación vive en la §2 de `mapa-maestro-medsemiotics-db.md` y las
> decisiones fechadas en su §8; lo que valida de verdad es `scripts/build.py`.
> Si este documento y el mapa discrepan, **manda el mapa**, y la discrepancia es
> un fallo de este archivo que se corrige aquí, no allí. Dos fuentes normativas
> del mismo contrato es exactamente el fallo que este repositorio ya arregló una
> vez, cuando `libro.py` y `epub.py` divergieron sin que nadie lo notara.

---

## Lo primero: teníais razón, y el fallo estaba en otro sitio

El valor no es binario y el formato lo obligaba a serlo. Eso es cierto.

Pero el ejemplo de la propuesta —`nombre: Hiperlipasemia (>3x)` con un `lr`
suelto— es el formato de vuestros protocolos, no el del índice. Aquí un signo
siempre fue `concepto: 'HM:0732'`: el umbral nunca estuvo congelado en el nombre.

El fallo real es peor y más callado. **El índice ya modelaba bandas** —la clave
`tramos`, en cinco condiciones— pero su frontera vivía *solo en prosa*:
`umbral: linfocitos atípicos ≥ 10%`, `rango: 7 a 10 (riesgo alto)`. Ningún
consumidor puede leer eso, así que el valor volvía a ser binario en cuanto salía
de aquí, y nadie lo notaba porque el libro se imprimía perfectamente.

Por eso el eje **no** entra como una clave `bandas` nueva: dos mecanismos de
banda conviviendo habría sido peor que ninguno. `graduacion` declara el eje y
cada tramo puede traer sus límites como números, **sin perder la prosa**, que
sigue siendo la etiqueta que imprime el libro.

## El contrato

```yaml
# condiciones/HM6003-mononucleosis-infecciosa.yaml
graduacion:
  parametro: Linfocitos atípicos    # qué se gradúa — obligatorio
  unidad: '%'                       # obligatoria en cuanto haya un número
  lectura: acumulativo              # acumulativo | disjunto — NO se infiere
tramos:
  - {umbral: 'linfocitos atípicos ≥ 10%', desde: 10, lr_positivo: 11.4, ref: 'pmid:27115266'}
  - {umbral: 'linfocitos atípicos ≥ 20%', desde: 20, lr_positivo: 26,   ref: 'pmid:27115266'}
  - {umbral: 'linfocitos atípicos ≥ 40%', desde: 40, lr_positivo: 50,   ref: 'pmid:27115266'}
  # Sin `desde`: criterio compuesto sobre dos recuentos, no un corte sobre un eje.
  - {umbral: 'linfocitos > 50% y atípicos > 10%', lr_positivo: 54, ref: 'pmid:27115266'}
```

| Clave | Dónde | Qué significa |
|---|---|---|
| `parametro` | graduacion | Qué valor del paciente se gradúa. Obligatorio: sin él los límites no dicen a qué comparar. |
| `unidad` | graduacion | Obligatoria en cuanto haya un tramo numérico. Se comprueba contra la unidad canónica del concepto. |
| `lectura` | graduacion | `acumulativo` o `disjunto`. Sin valor por defecto. |
| `desde` / `hasta` | tramo | Intervalo semiabierto `[desde, hasta)`. Omitir un extremo lo abre. |
| `umbral` | tramo | La prosa de la fuente. Sigue siendo la etiqueta impresa; opcional para vosotros. |
| `poblacion` | tramo | En qué población se midió ese corte. Prosa. |
| `ref` | tramo | Obligatorio, sin excepción por ser tramo. |

Un tramo sin `desde` ni `hasta` sigue siendo válido: es prosa honesta que no se
puede reducir a un corte sobre un eje. Vuestro extractor debe tratarlo como
ilegible y decirlo, no descartarlo en silencio.

## Cómo se lee un valor

Vuestra regla 1 —«los intervalos son semiabiertos y no se solapan»— habría
obligado a inventar cocientes, y por eso `lectura` se declara y no se infiere.

### `lectura: acumulativo`

```
  0        10        20        30        40        50   linfocitos atípicos, %
  ├─────────┼─────────┼─────────┼─────────┼─────────┤
            ●────────────────────────────────────────▶  ≥ 10 %  LR+ 11.4
                      ●──────────────────────────────▶  ≥ 20 %  LR+ 26   ← se aplica éste
                                          ●──────────▶  ≥ 40 %  LR+ 50
                           ▲
                       valor 25 %
```

Los cortes se **anidan a propósito**: la fuente midió «≥ 10 %», «≥ 20 %» y
«≥ 40 %» sobre poblaciones que se contienen unas a otras. Se aplica el **más
estricto que el valor satisface**. Partirlos en `[10,20)` y `[20,40)` para que no
se solapen daría tres cocientes que nadie midió.

### `lectura: disjunto`

```
  0               4           7               11   puntuación HEART
  ├───────────────┤ ←─hueco─→ ├───────────────┤
      LR− 0.20                     LR+ 13
    desde: 0                     desde: 7
    hasta: 4                     hasta: 11
```

**Cae en un tramo y sólo en uno.** Fijaos en el `hasta: 11` de un estrato que la
fuente escribe «7 a 10»: el intervalo es semiabierto, así que el 10 tiene que
entrar y el extremo superior no entra nunca. **No es una errata.**

Y el hueco de 4 a 6 es real: la fuente no publica ese cociente, así que una
puntuación de 5 significa que esta hipótesis no sabe leerla. Rellenarlo por
interpolación sería inventar.

## Los dos ejes, que no son intercambiables

Esto es lo que una clave `bandas` única habría aplanado, y es la parte que más
nos preocupa que se implemente mal.

| Clave del tramo | Gradúa | Qué hace el consumidor |
|---|---|---|
| `umbral` | El **hallazgo**. «≥ 10 %» y «≥ 20 %» son dos intensidades del mismo signo. | Busca dónde cae el valor del paciente. |
| `umbral_condicion` | La **condición contra la que se mide**. En el aneurisma, «≥ 3 cm» y «≥ 4 cm» son la misma palpación evaluada contra dos diagnósticos. | Elige según qué está preguntando. **El valor del paciente no entra aquí.** |

Una lista de tramos no puede mezclar los dos: es error de `build.py`. Así que el
discriminador ya es legible por máquina —qué clave trae el tramo— y no hizo falta
una clave nueva para decirlo.

Las escalas (HEART, TIMI, EGSYS) son un tercer caso: sus tramos usan `rango` como
prosa y no traen ninguno de los dos ejes, porque lo que se gradúa es la
puntuación misma. Cuelgan de `escalas`, no de `signos`, y no tienen concepto
`HM:` al que anclarse.

## Vuestras cinco reglas, contestadas

| Regla | Respuesta |
|---|---|
| 1 · Semiabiertos | **Aceptada, pero sólo bajo `disjunto`.** Es la regla que habría forzado a inventar cocientes en la mononucleosis. De ahí `lectura`. |
| 2 · Omitir abre | **Aceptada tal cual.** Escribir `desde: 0` afirmaría un límite que nadie midió. |
| 3 · `unidad` obligatoria | **Aceptada**, y elevada: la unidad canónica vive en el concepto, y la del tramo se comprueba contra ella. |
| 4 · Cada banda cita su fuente | **Ya era política aquí.** Un tramo sin `ref` nunca entró. |
| 5 · No cubrir toda la recta | **Ya estaba en los datos.** HEART declara 0–3 y 7–10 y deja fuera 4–6 desde antes de esta propuesta. |

### Una que dejáis abierta sin verla

`lr_negativo: 0.1` vive fuera de `bandas` en vuestra propuesta, y así **no dice a
qué corte llama «negativo»**. Es exactamente el número del que depende vuestro
ciclo 12: una prueba sensible negativa sólo descarta si «negativa» está definido
con precisión.

En el índice ya es error declarar un `lr_negativo` junto a tramos graduados sin
que declare su `umbral` o `umbral_condicion`. Podéis confiar en que está.

## Las cuatro preguntas que bloqueaban

| Pregunta | Decisión |
|---|---|
| `analito` | **No entra.** La identidad aquí es el código `HM:`, permanente y citado por los tres clientes. Un nombre en texto libre reintroduce la identidad-por-nombre que los códigos existen para evitar. `graduacion.parametro` describe, no identifica: no lo useis como clave. |
| Unidades canónicas | **Sí, en el concepto** (`umbral.unidad`). El tramo comprueba en vez de declarar, y la discrepancia se caza en el CI del índice. Ya rellenadas 19 de las 20 heredadas de la semilla. |
| `xLSN` o absoluto | **Ambos conviven** y `unidad` distingue cuál es. **El índice no convierte entre ellos**: hacerlo exige el LSN del laboratorio local, que el índice no conoce ni debe conocer. Se guarda la escala en la que la fuente publicó el corte. |
| Edad y sexo | **Entran ya, sin v2**, como `poblacion` del tramo — que es lo que son: otra población medida, no otra clave dentro de la banda. El solapamiento se comprueba dentro de cada población, porque el corte de varón y el de mujer se solapan por definición. |

Sobre la última: `poblacion` sigue siendo prosa, como en el resto del índice. Un
consumidor que no sepa a qué población pertenece su paciente **tiene que
decirlo** en vez de elegir un tramo. Estructurarla exige un vocabulario
controlado de poblaciones, que es otra decisión y más grande.

## Qué valida el índice, para que no lo dupliquéis

Vuestra lista de comprobaciones para CI ya corre aquí, en `scripts/build.py`, y
ninguna arista puede entrar sin pasarla:

- Dos tramos del mismo signo no se solapan bajo `disjunto` — y bajo
  `acumulativo` se comprueba lo contrario: cada corte es de un solo lado, todos
  al mismo lado, sin repetir corte.
- `desde < hasta` cuando ambos están.
- Cada tramo trae `ref`, y esa `ref` resuelve a una referencia del repositorio.
- Hay `unidad` y `parametro` si hay tramos numéricos, y no contradicen al
  concepto.
- Los tramos no mezclan `umbral` con `umbral_condicion`.
- El solapamiento se comprueba por población, no entre poblaciones.

Lo que **sí** os toca: decidir qué hacer con un valor que no cae en ningún tramo,
y con un tramo que no trae límites numéricos. La respuesta correcta en los dos
casos es la vuestra —decirlo en voz alta— y el índice no puede tomarla por
vosotros.

## Qué había en `main` el día de esta respuesta

Cinco bloques graduados, en cuatro condiciones. Es poco a propósito: sólo se
transcribió lo que ya estaba medido y en prosa, sin acuñar un solo cociente
nuevo. **Este inventario envejece**; el vigente sale del índice, no de aquí.

| Condición | Ancla | Unidad | Lectura | Eje | Tramos legibles |
|---|---|---|---|---|---|
| `HM:6003` | `HM:3004` · linfocitosis atípica | `%` | acumulativo | `umbral` | 3 de 4 |
| `HM:6006` | `HM:3012` · pulsación aórtica | `cm` | acumulativo | `umbral_condicion` | 2 de 2 |
| `HM:6007` | escala HEART | `puntos` | disjunto | `rango` | 2 de 2 |
| `HM:6007` | escala TIMI | `puntos` | disjunto | `rango` | 2 de 2 |
| `HM:6010` | escala EGSYS | `puntos` | disjunto | `rango` | 1 de 1 |

«3 de 4» en la mononucleosis: el cuarto tramo —`linfocitos > 50% y atípicos >
10%`, LR+ 54— se queda sin límites numéricos a propósito. Es un criterio
compuesto sobre dos recuentos, no un corte sobre un eje, y ponerle un número lo
haría legible al precio de que se leyera mal.

## Lo que sigue abierto

- **La unidad de la proteína C reactiva** (`HM:0761`). Un corte de 10 es
  plausible en mg/L —límite superior de normalidad— y en mg/dL —infección
  bacteriana—, y las dos lecturas se diferencian en un factor de 10. Se queda sin
  unidad hasta que la resuelva su fuente. Es el único de los 20 umbrales
  heredados que sigue así.
- **Vuestras conversiones.** Si un laboratorio informa lipasa en absoluto y el
  tramo está en `xLSN`, la conversión la hacéis vosotros con vuestro LSN, o no se
  hace. El índice no os dará el LSN porque no lo tiene.
- **La asimetría no cambia.** biosemiotics y medsemiotics leen del índice;
  vosotros seguís recibiendo los cambios como pull request que revisa y acepta un
  humano. Es lo primero que alguien optimizaría por descuido —«total, es sólo un
  `fetch`»— y rompería vuestra promesa de procesamiento local y vuestra
  auditabilidad a la vez.
