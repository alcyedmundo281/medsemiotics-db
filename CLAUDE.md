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
├── condiciones/*.yaml               ← síndromes y enfermedades, con sus LR y URLs
├── referencias/*.yaml               ← artículos con PMID y DOI
├── scripts/build.py                 ← valida; no modifica nada
├── scripts/banco.py                 ← carga el índice y extrae sus datos (sin tipografiar)
├── scripts/qmd.py                   ← proyecta el índice a un proyecto Quarto en build/quarto/
├── scripts/libro.py                 ← renderiza el PDF desde ese proyecto
├── scripts/epub.py                  ← renderiza el EPUB desde ese proyecto
├── scripts/paquete_latex.py         ← empaqueta build/quarto/ en un ZIP autocontenido
├── scripts/verificar_publicacion.py ← URLs públicas y figuras, en la fuente y en los derivados
├── scripts/auditar_medios.py        ← verifica SHA-1 y licencias CC contra Wikimedia
├── scripts/incorporar_medio.py      ← descarga e incorpora imágenes con atribución completa
├── assets/                          ← plantillas e imágenes locales
└── build/                           ← GENERADO, no se versiona (ver .gitignore)
    └── quarto/                      ← el proyecto Quarto: capítulos .qmd + libro.tex + imágenes
```

## Una fuente, un manuscrito, tres ediciones

`scripts/qmd.py` proyecta el índice a un **proyecto Quarto book** en
`build/quarto/`: un `_quarto.yml` más un capítulo `.qmd` por parte (Vocabulario,
Enfermedades, Síndromes) y las imágenes copiadas dentro. De ese único árbol
salen el EPUB, el PDF y la fuente del ZIP LaTeX. `libro.py` y `epub.py` ya no ensamblan nada:
eligen motor, renderizan y validan.

**Por qué se hizo así.** Antes había dos renderizadores del mismo contenido
—unas 900 líneas de LaTeX a mano en `libro.py` y un ensamblado Markdown propio
en `epub.py`— que había que mantener sincronizados a mano. Ya habían divergido:
el EPUB no tipografiaba `nucleo` ni `balance`, así que el núcleo diagnóstico de
las condiciones que lo declaran no aparecía en el libro electrónico y nadie lo
notó. Si dos salidas difieren en contenido, es un fallo de `qmd.py`, no una
variante editorial aceptable.

Sigue sin haber prosa que inventar: se tipografían los hechos que ya están en el
YAML —términos, sinónimos, umbrales, cocientes con su intervalo, y el
`decision`/`advertencia`/`motivo` que cada arista ya trae—. **Un campo que el
índice traiga y `qmd.py` no sepa tipografiar aborta la generación** en vez de
perderse en silencio; añadirlo al renderizador es parte del mismo cambio que lo
introduce en el índice.

Las citas **no** pasan por citeproc ni por biblatex: `banco.Citas` las numera en
orden de aparición y emite la referencia con el estilo de la casa, con PMID y
DOI como enlaces. Por eso la columna «Fuente» de la tabla de signos lleva `[3]`
y no la cita entera, cada condición cierra con sus propias fuentes, y la
bibliografía final separa lo que el libro cita de lo que el índice trae sin
citar todavía.

### El pipeline completo, en este orden

```bash
python scripts/build.py                                    # primero: valida el índice
python scripts/epub.py  --salida build/indice.epub         # EPUB (motor quarto, o pandoc)
python scripts/libro.py --salida build/libro.pdf           # PDF + build/quarto/libro.tex
python scripts/paquete_latex.py --salida build/medsemiotics-db-latex.zip
python scripts/verificar_publicacion.py --verificar-derivados --epub build/indice.epub
```

**El orden no es decorativo.** Cada generador reescribe `build/quarto/` entero,
y `libro.tex` solo existe después de renderizar el PDF: por eso el empaquetado y
la verificación de derivados van al final. Los dos abortan si falta, así que el
error es ruidoso, pero es evitable.

### El PDF

El compilador correcto es **LuaLaTeX, no pdflatex** (misma razón que
biosemiotics, sin relación de código: fontspec deja escribir ≥ ≤ → ± tal cual si
algún registro los trae, sin parchear glifo por glifo). `_quarto.yml` lo fija
con `pdf-engine: lualatex` y `mainfont: FreeSerif`, la fuente disponible que
cubre esos glifos sin fallback silencioso.

**La fuente LaTeX es un entregable, no un intermedio.** `keep-tex` la deja en
**`build/quarto/libro.tex`** —no en `build/libro.tex`, que ya no existe— junto a
las imágenes que `qmd.py` copió al proyecto. Ese directorio compila tal cual,
sin depender del checkout, y es lo que empaqueta `paquete_latex.py`:

```bash
cd build/quarto
lualatex -halt-on-error -interaction=nonstopmode libro.tex
```

**Dependencias de sistema:** `texlive-latex-recommended`, `texlive-latex-extra`,
`texlive-lang-spanish`, `texlive-luatex`, `fonts-freefont-ttf` y
**`librsvg2-bin`**. Este último no es opcional: dos figuras del índice son SVG y
LaTeX no incluye SVG, así que Quarto las convierte con `rsvg-convert` o aborta
el PDF; rasteriza además la portada, que Kindle no admite en SVG. **`biber` ya
no hace falta**: el `.tex` de Quarto no usa biblatex.

### El EPUB

`epub.py` prefiere `quarto` y cae a `pandoc` sobre `build/quarto/libro-plano.md`
—el mismo libro aplanado, escrito concatenando los MISMOS capítulos— cuando
Quarto no está instalado. Fuerza uno u otro con `--motor quarto|pandoc`.

CI fija Quarto **1.5.57** y Pandoc **3.1.11** (paquete oficial, no `apt`),
conservando la versión comprobada con los SVG en el PR #3.
Todas las imágenes de conceptos y condiciones se incluyen, también las
adicionales y las de conceptos sin aristas. El EPUB las verifica por SHA-256
y por sus enlaces desde XHTML, no por el número de archivos del ZIP.

El respaldo usa el lector `markdown` de pandoc, no `gfm`. Con `gfm` se perdían
tres cosas a la vez: los atributos `{#sec-...}` se filtraban como texto al
índice, las listas de definiciones del vocabulario se aplanaban a párrafos
sueltos, y el pie de figura se reducía a un `alt=` de texto plano —`gfm` acepta
`implicit_figures` pero la ignora—, con lo que los enlaces de crédito y licencia
de cada imagen desaparecían del contenedor sin que fallara nada.

**No uses la clave `part:` de Quarto.** Su escritor de EPUB no emite páginas
divisorias de parte. Por eso `_quarto.yml` lleva una lista plana de capítulos y
la parte es el capítulo del libro. Tampoco declares `identifier` ni `rights`
bajo `book:`: no son propiedades válidas de ese esquema, y al nivel superior
Quarto las pasa a pandoc *además* del `epub-metadata.xml`, dejando dos
`dc:identifier` en el OPF.

El DOI, el ORCID, la licencia y las materias del contenedor salen de
**`CITATION.cff`**, que ya es la autoridad para GitHub y para Zenodo. No se
copian a mano en ningún `.py`.

`refs.bib` se deriva de `referencias/*.yaml` en cada corrida —no se versiona— y
viaja dentro del paquete LaTeX aunque el libro ya no use biblatex: es el archivo
que citan por `clave_bibtex` las fichas de biosemiotics.

### Verificar la publicación

```bash
python scripts/verificar_publicacion.py                    # URLs y figuras del índice
python scripts/verificar_publicacion.py --id HM:6001 --url "https://..." --comprobar-web
python scripts/verificar_publicacion.py --verificar-derivados --epub build/indice.epub
python scripts/verificar_publicacion.py --verificar-derivados --epub build/control-pandoc.epub --pdf build/libro.pdf
```

`--pdf` requiere `pypdf` y comprueba códigos y enlaces clicables en el PDF
final. CI también descomprime el ZIP fuera del checkout y lo compila.
Las regresiones se ejecutan con `python -m unittest discover -s scripts/tests -v`.
Los destinos de generación deben ser subdirectorios de `build/`; el generador
solo reemplaza directorios que lleven su marca en `_quarto.yml`.

Un enlace mal escrito o una figura que se quedó fuera del contenedor no rompen
ninguna compilación: sale un libro perfectamente válido que apunta a una página
que no existe o publica una imagen sin su crédito. Esto lo convierte en un fallo
ruidoso. `--comprobar-web` es opcional a propósito, para que un fallo transitorio
de red no vuelva inestable la integridad local.

El workflow `.github/workflows/libro.yml` reproduce este contrato completo
—validación, EPUB por los dos motores, LuaLaTeX, EPUBCheck y verificación de
derivados— en cada push o PR que toque el índice, `CITATION.cff` o los scripts, y
publica `libro.pdf`, `libro.tex`, `indice.epub` y el ZIP como artifacts (90 días)
o, en un release, como assets adjuntos. `workflow_dispatch` queda como
recuperación manual.

## Lo primero al arrancar una sesión

1. `git status` y reporta el estado.
2. Lee `mapa-maestro-medsemiotics-db.md` y di **qué oleada toca**.
3. `python scripts/build.py` y reporta las alertas actuales.
4. `python scripts/verificar_publicacion.py` (sin `--verificar-derivados`: no
   necesita el libro compilado) y reporta si alguna URL o figura está rota.

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
