"""Regresiones de cobertura de imágenes; no requieren Pandoc."""
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import epub


class ImagenesEpubTest(unittest.TestCase):
    def setUp(self):
        self.temporal = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporal.cleanup)
        self.raiz = Path(self.temporal.name)
        self.indice = epub.motor.Indice(self.raiz)

    def medio(self, nombre):
        (self.raiz / nombre).write_bytes(nombre.encode())
        return dict(
            tipo="imagen", descripcion=nombre, credito="Autor",
            fuente="Archivo", fuente_url="https://example.org/fuente",
            licencia_img="CC0", licencia_url="https://example.org/licencia",
            archivo_local=nombre,
        )

    def contenedor(self, archivos):
        salida = self.raiz / "prueba.epub"
        with zipfile.ZipFile(salida, "w") as zf:
            zf.writestr("mimetype", "application/epub+zip")
            zf.writestr("META-INF/container.xml", "<container/>")
            zf.writestr("EPUB/texto.xhtml", "Bibliografía" + " " * 22000)
            for archivo in archivos:
                zf.write(self.raiz / archivo, "EPUB/media/" + archivo)
        return salida

    def test_todas_las_imagenes_incluso_sin_aristas(self):
        medios = [self.medio(n) for n in ("uno.jpg", "dos.svg", "aislado.png", "condicion.jpg")]
        self.indice.conceptos = {
            "HM:3001": dict(termino="Relacionado", medios=medios[:2]),
            "HM:3002": dict(termino="Aislado", medios=[medios[2]]),
        }
        self.indice.condiciones_por_archivo = {
            "HM:6001": dict(clase="enfermedad", termino="Sin signos", medios=[medios[3]]),
            "HM:6002": dict(clase="enfermedad", termino="Con signos", signos=[
                dict(concepto="HM:3001", rol="apoyo", estado_lr="no_medido")
            ]),
        }
        # Repite la arista para comprobar que cada concepto se ilustra una vez.
        figuras = epub.figuras_de_condicion_md(
            self.indice, [{"concepto": "HM:3001"}] * 2, "condición"
        )
        self.assertEqual(sum(linea.startswith("![") for linea in figuras), 2)
        texto = epub.manuscrito(self.indice, "test")
        for medio in medios:
            self.assertEqual(texto.count("](" + medio["archivo_local"] + ")"), 1)

    def test_segunda_imagen_sin_atribucion_aborta(self):
        medios = [self.medio("uno.jpg"), self.medio("dos.svg")]
        del medios[1]["credito"]
        with self.assertRaisesRegex(epub.motor.ErrorGeneracion, "medio 2 sin credito"):
            epub.figuras_de_registro_md(self.indice, {"medios": medios}, "HM:3001")

    def test_misma_cantidad_no_oculta_imagen_omitida(self):
        self.indice.conceptos = {"HM:3001": {"medios": [self.medio("esperada.svg")]}}
        self.medio("ajena.svg")
        with self.assertRaisesRegex(epub.motor.ErrorGeneracion, "esperada.svg"):
            epub.validar_epub(self.contenedor(["ajena.svg"]), self.indice, 1)

    def test_imagen_compartida_no_exige_archivos_duplicados(self):
        medio = self.medio("compartida.svg")
        self.indice.conceptos = {"HM:3001": {"medios": [medio]}}
        self.indice.condiciones_por_archivo = {"HM:6001": {"medios": [medio]}}
        epub.validar_epub(self.contenedor(["compartida.svg"]), self.indice, 2)


if __name__ == "__main__":
    unittest.main()
