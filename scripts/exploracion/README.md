# scripts/exploracion/

Análisis puntuales que sustentan decisiones del proyecto. **No forman parte del
pipeline**: no se ejecutan de forma periódica y ninguno escribe en el índice.

Están aquí porque las conclusiones sí quedaron —en el mapa maestro, en los
README, en los mensajes de commit— pero la medición que las produjo se habría
perdido. Un número sin el código que lo calculó no se puede rebatir.

Las rutas salen de variables de entorno: `TMP_TRABAJO`, `BIOSEMIOTICS_REPO`,
`MEDSEMIOTICS_REPO`, `HOLONMED_SKILLS`, `TAXONOMIA_DIR`, `TOPICS_JSONL_DIR`.
Por defecto apuntan al directorio actual, así que hay que darles valor.

## Qué decidió cada uno

### `calidad_topics.py` · `normalizacion_ensayo.py`
Por qué se descartó el primer archivo de temas.

Midieron que el 27% de sus 1141 términos eran fragmentos de texto corrido
—*«Chronic Diarrhea and»*, *«Rhonchus). Test similarly with the»*— y que una
normalización agresiva solo reducía el ruido un 9%: el problema no era de
formato sino de extracción, y ninguna expresión regular lo arreglaba.

### `comparar_taxonomias.py` · `unir_taxonomias.py`
Por qué se eligió `processed_data_medical_taxonomy` y se descartó el tercero.

Descubrieron que dos de los tres archivos son **complementarios** —uno aporta
`type`, el otro `differential_diagnosis`— y están alineados fila a fila al 100%,
mientras que el tercero es un derivado empobrecido: solo 5 términos suyos no
están en los otros, frente a 103 que le faltan. También sacaron a la luz el eje
`SIGN`/`SYNDROME`/`DISEASE`, que es el que estructura el índice.

### `cobertura_biosemiotics.py`
Qué siembra biosemiotics y qué no.

Confirmó que sus 14 signos traen la tríada completa y que su `refs.bib` tiene
PMID y DOI en las 74 entradas. Y sobre todo lo contrario: **cero** LR, códigos,
condiciones o sinónimos. Su `decision` es prosa clínica, no un cociente. De ahí
que la capa de aristas haya que escribirla y no se pueda sembrar.

### `ejes_medsemiotics.py` · `generable_medsemiotics.py` · `sondeo_clasificacion.py`
Dónde cae la frontera entre lo estático y lo vivo.

Clasificaron las 107 páginas publicadas de medsemiotics por eje temático y por
forma. El dato que zanjó la discusión: 38 son aplicaciones —`codigo_estadistico`
tiene 93.778 caracteres de JavaScript y 1.303 de texto— y solo 48 son
documentos. Menos de la mitad del sitio es generable desde una fuente
estructurada, y no por falta de disciplina.

### `parametrizar_rutas.py`
Mantenimiento puntual: convirtió las rutas absolutas de los scripts del pipeline
en variables de entorno. Se conserva como registro de esa operación; no hace
falta volver a ejecutarlo.
