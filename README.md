# medsemiotics-db

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.22064424.svg)](https://doi.org/10.5281/zenodo.22064424)

**Índice de conocimiento clínico verificado.** Conceptos, condiciones y
referencias en YAML, con PMID y DOI comprobados. Sin prosa, sin presentación,
sin didáctica.

Es un **proveedor**: no publica nada por sí mismo. De él se sirven
[holonmed](https://github.com/alcyedmundo281/holonmed) para validar hallazgos y
razonar, [biosemiotics](https://github.com/alcyedmundo281/biosemiotics) para su
atlas y [medsemiotics](https://github.com/alcyedmundo281/medsemiotics) para su
plataforma educativa.

La arquitectura es la de PubMed y PMC: aquí vive el índice, el texto completo
vive en cada cliente.

## Qué contiene

```
conceptos/     signos y hallazgos: identidad, sinónimos, jerarquía, umbrales
condiciones/   síndromes y enfermedades, con sus aristas ponderadas (LR)
referencias/   artículos con PMID y DOI verificados
scripts/       build.py valida; qmd.py proyecta; libro.py/epub.py renderizan
build/         GENERADO (quarto/, libro.pdf, indice.epub, ZIP LaTeX) — no se versiona
```

La tríada del proyecto queda repartida así:

| | dónde vive | depende del contexto |
|---|---|---|
| **signo** — lo que se ve | `conceptos/` · `significante` | no |
| **interpretación** — la realidad clínica | `conceptos/` · `significado` | no |
| **decisión** — el consejo del experto | `condiciones/` · `LR` + `rol` | **sí** |

Los dos primeros valen siempre. El tercero no: la hiperlipasemia tiene LR 26.6
**para pancreatitis aguda**, no en abstracto. Por eso el cociente pertenece a la
arista concepto→condición y no al concepto suelto.

## Estado

| capa | registros |
|---|---|
| referencias | **100** — verificadas contra PubMed |
| conceptos | **223** — 25 con umbral |
| condiciones | **21** |
| aristas con LR | **74** |

Ver [mapa-maestro-medsemiotics-db.md](mapa-maestro-medsemiotics-db.md) para el
plan completo y las oleadas pendientes.

## Uso

```bash
python scripts/build.py
```

Valida todos los registros y reporta qué falta. No modifica nada.

## Salidas derivadas

Una fuente, **un manuscrito**, tres ediciones. `scripts/qmd.py` proyecta el
índice a un proyecto [Quarto](https://quarto.org) book en `build/quarto/`, y de
ese único árbol salen el EPUB3, el PDF en LuaLaTeX y el ZIP con la fuente LaTeX
autocontenida. Ninguna añade prosa — tipografían los mismos hechos que ya están
en el YAML.

```bash
python scripts/build.py                                    # valida el índice
python scripts/epub.py  --salida build/indice.epub         # EPUB3
python scripts/libro.py --salida build/libro.pdf           # PDF + build/quarto/libro.tex
python scripts/paquete_latex.py --salida build/medsemiotics-db-latex.zip
python scripts/verificar_publicacion.py --verificar-derivados --epub build/indice.epub --pdf build/libro.pdf
```

El orden importa: cada generador reescribe `build/quarto/` entero y `libro.tex`
solo existe tras renderizar el PDF. `epub.py` prefiere Quarto y cae a Pandoc
sobre el mismo libro aplanado si Quarto no está instalado.

CI fija Quarto **1.5.57** y Pandoc **3.1.11**. Comprueba ambos EPUB, los enlaces
del PDF final y la compilación del ZIP fuera del repositorio. La verificación
del PDF requiere `pypdf`, además de PyYAML para el índice.

Ver `CLAUDE.md` para las dependencias de sistema —incluida `librsvg2-bin`, sin
la cual el PDF no compila porque el índice trae figuras SVG—.
`.github/workflows/libro.yml` reproduce todo el contrato en CI, valida el EPUB
con EPUBCheck y publica los artifacts en cada push a `main` y en cada release.

## Reglas duras

- **Ningún LR entra sin `ref` resoluble.** Un cociente sin procedencia es un
  número inventado con formato científico, y mueve la probabilidad que ve un
  clínico.
- **PubMed es la autoridad** para título, año y estado de retractación.
  CrossRef solo confirma que el DOI resuelve: sus títulos vienen truncados o
  con erratas con frecuencia suficiente como para no fiarse.
- **Los códigos `HM:` son permanentes.** Una vez publicados, otros sistemas los
  citan. No se renumeran ni se reutilizan.
- **Aquí no hay prosa.** Si un dato necesita explicarse para entenderse, va en
  medsemiotics o en biosemiotics, no aquí.
- **El índice propone, no impone.** holonmed recibe los cambios como pull
  request y los acepta un humano. Ningún cliente consulta este repositorio en
  tiempo de ejecución.

## Licencia

[CC0 1.0 Universal](LICENSE) — dominio público.

El contenido son hechos: términos, códigos, umbrales y cocientes publicados.
Una licencia restrictiva sobre un conjunto de hechos reclamaría algo que no
corresponde, e impediría que lo consuman a la vez proyectos con licencias
distintas —hoy AGPL-3.0, CC BY-NC 4.0 y CC BY-SA 4.0—.
