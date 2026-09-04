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


if __name__ == "__main__":
    unittest.main()
