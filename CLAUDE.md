# CLAUDE.md — Manual de operación de medsemiotics-db

Este archivo le enseña a cualquier sesión de Claude Code cómo trabajar en este
repositorio. **Léelo completo al arrancar.** No improvises el flujo.

---

## Qué es este proyecto

El índice de conocimiento clínico del ecosistema Powersemiotics. Conceptos,
condiciones y referencias verificadas, en YAML. **Proveedor, no publicador.**

Autor y responsable clínico: Dr. Alcy Torres. Toda decisión clínica final es
suya.

## Regla de oro

**Aquí solo entran hechos.** Un umbral, un código, un sinónimo, un cociente de
verosimilitud con su fuente. Si un dato necesita un párrafo para entenderse, es
prosa y pertenece a medsemiotics o a biosemiotics.

La prueba práctica: *¿esto se discute en un PR de tres líneas o requiere leer un
artículo?* Lo primero es estructura; lo segundo es didáctica.

## Mapa del repositorio

```
medsemiotics-db/
├── CLAUDE.md                        ← este archivo
├── mapa-maestro-medsemiotics-db.md  ← QUÉ poblar y en qué orden (léelo siempre)
├── conceptos/*.yaml                 ← signos y hallazgos
├── condiciones/*.yaml               ← síndromes y enfermedades, con sus LR
├── referencias/*.yaml               ← artículos con PMID y DOI
└── scripts/build.py                 ← valida; no modifica nada
```

No hay `build/` porque no hay salidas derivadas todavía. Cuando las haya
—index.json, JSON-LD—, serán generadas y no se editarán a mano.

## Lo primero al arrancar una sesión

1. `git status` y reporta el estado.
2. Lee `mapa-maestro-medsemiotics-db.md` y di **qué oleada toca**.
3. `python scripts/build.py` y reporta las alertas actuales.

## Reglas duras (no se rompen nunca)

- **Ningún LR sin `ref` resoluble.** Un cociente sin procedencia es un número
  inventado con formato científico. Es la regla que más importa del repositorio.
- **Citas solo verificadas.** Nunca escribas una referencia de memoria ni
  aceptes una que produjo un modelo sin comprobar el PMID. Este ecosistema ya
  fue salvado de tres referencias inventadas en biosemiotics.
- **PubMed manda sobre CrossRef.** PubMed es autoridad para título, año y
  retractación; CrossRef solo confirma que el DOI resuelve. Comprobado sobre las
  74 referencias iniciales: cuatro títulos de CrossRef están truncados o con
  erratas —una dice «Critically III» desde 1995—. Comparar títulos contra
  CrossRef genera falsas alarmas.
- **Los códigos `HM:` son permanentes.** No se renumeran, no se reutilizan, no
  se reasignan. Otros sistemas los citan.
- **Antes de acuñar un código nuevo, busca si el término ya existe.** El
  vocabulario semilla trae 136 conceptos con 114 conjuntos de sinónimos.
  Duplicar un concepto es el error más caro de deshacer.
- **`estado_lr` distingue `no_medido` de `sin_efecto`.** No son lo mismo:
  holonmed necesita saber si ignorar la arista o tratarla como neutra.
- **Nada de prosa.** Ni `abstract`, ni `descripcion`, ni notas explicativas en
  los registros. Las `notas` de verificación son la única excepción y describen
  el estado del dato, no el concepto.

## La asimetría con holonmed

biosemiotics y medsemiotics **leen** de este índice. holonmed **no**: recibe los
cambios como pull request que revisa y acepta un humano.

Esa asimetría preserva su promesa de procesamiento local y su auditabilidad. Es
lo primero que alguien optimizaría por descuido —«total, es solo un `fetch`»— y
rompería las dos cosas a la vez. **No lo hagas.**

## Flujo para añadir una condición con sus aristas

1. **Ubícala en el mapa maestro.** Copia su tipo y su oleada.
2. **Comprueba que sus signos existen** como conceptos. Si no, créalos primero:
   una arista que apunta a un concepto inexistente falla en silencio.
3. **Cada LR necesita**: valor, población en la que se midió, intervalo de
   confianza si consta, y `ref` a una referencia del repositorio.
4. **Si no hay LR publicado**, la arista se crea igual con
   `estado_lr: no_medido`. La relación existe aunque nadie la haya cuantificado.
5. `python scripts/build.py`. No continúes con errores.

## Añadir una referencia

No se escriben a mano. Se obtienen por PMID y se verifican contra PubMed; el
DOI se confirma contra CrossRef. El registro guarda ambos identificadores más la
`clave_bibtex` original, que es la que citan hoy las fichas de biosemiotics: sin
ella la migración no puede resolver `refs: [lichtenstein2008]`.

## Qué NO hacer

- No edites un registro para «mejorar la redacción»: no hay redacción que
  mejorar.
- No inventes el final de un término truncado. Los 122 términos con marcas de
  corte del temario se reparan a mano contra la fuente, no se adivinan.
- No mezcles los ejes de clasificación. `sistema`/`organo`/`ventana`/`sonda` son
  de biosemiotics y específicos de ecografía; aquí el eje es
  `concepto`/`condicion` y la `semantica`.
