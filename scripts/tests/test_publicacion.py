"""Regresiones del manuscrito único y de las garantías de imágenes del PR #3."""
import shutil
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import banco
import libro
import qmd
import verificar_publicacion as verificar

RAIZ = Path(__file__).resolve().parents[2]


class PublicacionTest(unittest.TestCase):
    def setUp(self):
        temporal = tempfile.TemporaryDirectory()
        self.addCleanup(temporal.cleanup)
        self.raiz = Path(temporal.name)
        shutil.copy2(RAIZ / "CITATION.cff", self.raiz / "CITATION.cff")
        self.indice = banco.Indice(self.raiz)
        self.indice.conceptos = {"HM:3001": dict(termino="Hallazgo", id="HM:3001")}
        self.indice.condiciones_por_archivo = {
            "HM:6001": dict(id="HM:6001", clase="enfermedad", termino="Condición")
        }
        self.indice.referencias = {
            f"pmid:{n}": dict(id=f"pmid:{n}", clave_bibtex=f"ref{n}", titulo=f"Fuente {n}", identificadores={})
            for n in (1, 2, 3)
        }
        self.citas = banco.Citas(self.indice)

    def medio(self, nombre):
        (self.raiz / nombre).write_bytes(nombre.encode())
        return dict(tipo="imagen", descripcion=nombre, credito="Autor", fuente="Archivo",
                    fuente_url="https://example.org/fuente", licencia_img="CC0",
                    licencia_url="https://example.org/licencia", archivo_local=nombre)

    def epub(self, archivos, enlazados):
        salida = self.raiz / "prueba.epub"
        with zipfile.ZipFile(salida, "w") as zf:
            zf.writestr("mimetype", "application/epub+zip")
            imagenes = "".join(f'<img src="media/{n}"/>' for n in enlazados)
            zf.writestr("EPUB/texto.xhtml", '<html xmlns="http://www.w3.org/1999/xhtml"><body>'
                        'HM:3001 HM:6001 <a href="https://example.org/fuente">Fuente</a>'
                        '<a href="https://example.org/licencia">Licencia</a>' + imagenes + '</body></html>')
            for archivo in archivos:
                zf.write(self.raiz / archivo, "EPUB/media/" + archivo)
        return salida

    def test_todas_las_imagenes_y_manuscrito_literal(self):
        medios = [self.medio(n) for n in ("uno.jpg", "dos.svg", "aislado.png", "condicion.jpg", "raiz.jpg")]
        self.indice.conceptos["HM:3001"]["medios"] = medios[:2]
        self.indice.conceptos["HM:3002"] = dict(termino="Aislado", medios=[medios[2]])
        self.indice.conceptos["HM:0100"] = dict(termino="Raíz de grupo", medios=[medios[4]])
        self.indice.condiciones_por_archivo["HM:6001"]["medios"] = [medios[3]]
        self.indice.condiciones_por_archivo["HM:6002"] = dict(
            id="HM:6002", clase="enfermedad", termino="Con signos",
            signos=[dict(concepto="HM:3001", rol="apoyo", estado_lr="no_medido")] * 2)
        destino = self.raiz / "build" / "quarto"
        with patch("qmd.rasterizar_portada", return_value=False):
            informe = qmd.generar(self.indice, self.raiz, destino)
        plano = (destino / "libro-plano.md").read_text(encoding="utf-8")
        esperado = "\n\n".join((destino / n).read_text(encoding="utf-8")
                               for n in informe["capitulos"] + informe["apendices"])
        self.assertEqual(plano, esperado)
        self.assertEqual(informe["figuras"], 5)
        for medio in medios:
            self.assertEqual(plano.count("](" + medio["archivo_local"] + ")"), 1)
            self.assertTrue((destino / medio["archivo_local"]).is_file())

    def test_segunda_imagen_sin_credito_aborta(self):
        medios = [self.medio("uno.jpg"), self.medio("dos.svg")]
        del medios[1]["credito"]
        with self.assertRaisesRegex(banco.ErrorGeneracion, "medio 2 sin credito"):
            banco.imagenes_de_registro(self.indice, {"medios": medios}, "HM:3001")

    def test_misma_cantidad_no_oculta_imagen_omitida(self):
        self.indice.conceptos["HM:3001"]["medios"] = [self.medio("esperada.svg")]
        self.medio("ajena.svg")
        errores = []
        verificar.validar_contenido_epub(self.indice, self.epub(["ajena.svg"], ["ajena.svg"]), errores)
        self.assertTrue(any("esperada.svg" in e for e in errores))

    def test_imagen_incrustada_pero_no_enlazada_falla(self):
        self.indice.conceptos["HM:3001"]["medios"] = [self.medio("esperada.svg")]
        errores = []
        verificar.validar_contenido_epub(self.indice, self.epub(["esperada.svg"], []), errores)
        self.assertTrue(any("esperada.svg" in e for e in errores))

    def test_imagen_compartida_no_exige_duplicados(self):
        medio = self.medio("compartida.svg")
        self.indice.conceptos["HM:3001"]["medios"] = [medio]
        self.indice.condiciones_por_archivo["HM:6001"]["medios"] = [medio]
        errores = []
        verificar.validar_contenido_epub(self.indice, self.epub(["compartida.svg"], ["compartida.svg"]), errores)
        self.assertEqual(errores, [])

    def test_nucleo_balance_y_covariables(self):
        condicion = self.indice.condiciones_por_archivo["HM:6001"]
        condicion.update(nucleo=dict(requiere=["HM:3001"], ref="pmid:1"),
                         balance=dict(ref="pmid:2", establecida=dict(apoyos_minimos=2)),
                         signos=[dict(concepto="HM:3001", estado_lr="no_medido", efecto="excluye",
                                      dispara_si="ausente", sostiene="consenso_con_afirmacion",
                                      odds_ratio=dict(valor=2.7, ic95=[1.4, 5.1], ref="pmid:3", covariables="edad y sexo"))])
        texto = qmd.capitulo_condicion(self.indice, "HM:6001", condicion, self.citas, [])
        for fragmento in ("Núcleo diagnóstico", "Hallazgo", "Balance diagnóstico", "apoyos\\_minimos: 2",
                          "Excluye", "ausente", "consenso con afirmacion", "OR 2.7", "edad y sexo"):
            self.assertIn(fragmento, texto)
        self.assertEqual(len(self.citas.orden), 3)

    def test_umbrales_componentes_y_escalas_no_pierden_datos(self):
        concepto = dict(termino="Lipasa", componentes=["componente A"],
                        umbral=dict(parametro="Lipasa", corte_superior=60, multiplicador=3, ref="pmid:1"))
        texto = "\n".join(qmd.entrada_concepto_md("HM:3001", concepto, self.citas))
        self.assertIn("multiplicador: 3", texto)
        self.assertIn("componente A", texto)
        escala = dict(escalas=[dict(nombre="EGSYS", tramos=[dict(lr_negativo_rango=[0.12, 0.17],
                                                              ic95=[0.1, 0.2], ref="pmid:2")])])
        texto = "\n".join(qmd.bloque_escalas(escala, self.citas, "prueba"))
        self.assertIn("0.12 / 0.17", texto)
        self.assertIn("IC95%", texto)
        self.assertEqual(self.citas.orden, ["pmid:1", "pmid:2"])

    def test_probabilidad_base_no_pierde_ic95_ni_nota(self):
        """Estaba tirando en silencio el IC95 de tres condiciones y la nota de otras tres."""
        condicion = dict(
            self.indice.condiciones_por_archivo["HM:6001"],
            probabilidad_base=dict(valor=0.19, ic95=[0.16, 0.23],
                                   poblacion="ambulatorios con sospecha",
                                   nota="depende del cribado", ref="pmid:1"),
        )
        texto = qmd.capitulo_condicion(self.indice, "HM:6001", condicion, self.citas, [])
        # `frase()` capitaliza la nota, de ahí la mayúscula.
        for fragmento in ("19%", "IC95% 16%–23%", "ambulatorios con sospecha",
                          "Depende del cribado"):
            self.assertIn(fragmento, texto)

    def test_probabilidad_base_con_clave_desconocida_aborta(self):
        condicion = dict(
            self.indice.condiciones_por_archivo["HM:6001"],
            probabilidad_base=dict(valor=0.19, inventada=1, ref="pmid:1"),
        )
        with self.assertRaisesRegex(banco.ErrorGeneracion, "probabilidad_base"):
            qmd.capitulo_condicion(self.indice, "HM:6001", condicion, self.citas, [])

    def test_tramo_sin_umbral_se_rotula_por_su_poblacion(self):
        """Seis mediciones del mismo signo en estratos distintos: la fila necesita nombre."""
        arista = dict(concepto="HM:3001", rol="prueba_sensible", estado_lr="medido",
                      lr_negativo=dict(valor=0.10, ref="pmid:1"),
                      tramos=[dict(poblacion="sospecha baja, ensayo sensible",
                                   lr_negativo=0.10, ref="pmid:1"),
                              dict(poblacion="sospecha alta, ensayo sensible",
                                   lr_negativo=0.07, ref="pmid:1")])
        filas, notas = banco.filas_de_signo(self.indice, arista, "prueba")
        etiquetas = [f.etiqueta for f in filas]
        self.assertEqual(etiquetas,
                         ["Hallazgo (sospecha baja, ensayo sensible)",
                          "Hallazgo (sospecha alta, ensayo sensible)"])
        self.assertNotIn("?", " ".join(etiquetas))
        # y no se repite como nota al pie lo que ya es la etiqueta de la fila
        self.assertFalse([e for e, _ in notas if e.endswith("— poblacion")
                          and "sospecha baja" in e])

    def test_numeracion_global_con_saltos(self):
        for n in (1, 2, 3):
            self.citas.marca(f"pmid:{n}", "prueba")
        lista = self.citas.lista(["pmid:1", "pmid:3"])
        self.assertTrue(lista[0].startswith("\\[1\\]"))
        self.assertTrue(lista[2].startswith("\\[3\\]"))

    def test_campo_desconocido_aborta(self):
        condicion = dict(self.indice.condiciones_por_archivo["HM:6001"], desconocido=123)
        with self.assertRaisesRegex(banco.ErrorGeneracion, "sin renderizador"):
            qmd.capitulo_condicion(self.indice, "HM:6001", condicion, self.citas, [])

    def test_no_borra_fuentes_ni_directorios_ajenos(self):
        for destino in (self.raiz, self.raiz / "conceptos", self.raiz / "build"):
            with self.assertRaises(banco.ErrorGeneracion):
                qmd.generar(self.indice, self.raiz, destino)
        destino = self.raiz / "build" / "ajeno"
        destino.mkdir(parents=True)
        archivo = destino / "conservar.txt"
        archivo.write_text("conservar")
        with self.assertRaises(banco.ErrorGeneracion):
            qmd.generar(self.indice, self.raiz, destino)
        self.assertEqual(archivo.read_text(), "conservar")


class RasterizadorTest(unittest.TestCase):
    """El PDF necesita `rsvg-convert`, y decirlo antes cuesta menos que después.

    Sin él Quarto aborta con un volcado de Lua que no nombra la dependencia.
    Estas pruebas fijan las dos mitades del contrato: se exige cuando hay SVG,
    y no se exige cuando no lo hay.
    """

    def informe(self, *nombres):
        return {"figuras_detalle": [
            (f"HM:300{n}", dict(archivo_local=nombre))
            for n, nombre in enumerate(nombres, start=1)
        ]}

    def test_svg_sin_rasterizador_aborta_nombrando_la_dependencia(self):
        informe = self.informe("assets/img/uno.png", "assets/img/dos.SVG")
        with patch("shutil.which", return_value=None):
            with self.assertRaises(banco.ErrorGeneracion) as fallo:
                libro.exigir_rasterizador(informe)
        mensaje = str(fallo.exception)
        self.assertIn("rsvg-convert", mensaje)
        self.assertIn("librsvg2-bin", mensaje)
        # y dice cuál es la figura que lo obliga, no sólo que falta algo
        self.assertIn("assets/img/dos.SVG", mensaje)
        self.assertNotIn("uno.png", mensaje)

    def test_svg_con_rasterizador_pasa(self):
        informe = self.informe("assets/img/dos.svg")
        with patch("shutil.which", return_value="/usr/bin/rsvg-convert"):
            self.assertIsNone(libro.exigir_rasterizador(informe))

    def test_sin_svg_no_se_exige_una_dependencia_que_no_se_usa(self):
        informe = self.informe("assets/img/uno.png", "assets/img/tres.jpg")
        with patch("shutil.which", return_value=None):
            self.assertIsNone(libro.exigir_rasterizador(informe))


class ResumenDerivadosTest(unittest.TestCase):
    """El resumen nombra lo que se comprobó, ni más ni menos.

    Callaba el PDF aunque `validar_pdf` lo hubiera recorrido entero: quien leía
    la salida concluía que no se había verificado.
    """

    def test_nombra_el_pdf_que_acaba_de_verificar(self):
        self.assertEqual(
            verificar.resumen_derivados(True, True, True),
            "✓ Derivados coherentes: libro.tex, libro aplanado, EPUB y PDF")

    def test_sin_epub_no_lo_nombra(self):
        self.assertEqual(
            verificar.resumen_derivados(True, False, False),
            "✓ Derivados coherentes: libro.tex y libro aplanado")

    def test_solo_pdf_tambien_se_anuncia(self):
        # `--pdf` sin `--verificar-derivados` comprobaba en silencio
        self.assertEqual(verificar.resumen_derivados(False, False, True),
                         "✓ Derivados coherentes: PDF")

    def test_sin_comprobar_nada_no_hay_linea(self):
        self.assertEqual(verificar.resumen_derivados(False, False, False), "")


if __name__ == "__main__":
    unittest.main()
