"""Regresión: regenerar una referencia no puede borrar el cotejo de su errata.

`6_referencia_por_pmid.py` reescribe el registro entero en cada corrida. Sin
conservar lo añadido a mano, una regeneración borraría `errata_verificada` y las
notas de quien fue a mirar la corrección —y el borrado sería invisible: el
registro volvería a estar bloqueado sin que nadie supiera que se desbloqueó—.
"""
import importlib
import sys
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "scripts"))
generador = importlib.import_module("6_referencia_por_pmid")


class ConservacionTest(unittest.TestCase):
    def escribe(self, texto):
        temporal = tempfile.TemporaryDirectory()
        self.addCleanup(temporal.cleanup)
        destino = Path(temporal.name) / "pmid-1.yaml"
        destino.write_text(texto, encoding="utf8")
        return destino

    def test_conserva_el_cotejo_y_descarta_lo_generado(self):
        destino = self.escribe("""\
id: 'pmid:1'
verificacion:
  pubmed: true
  fecha: 2026-08-23
  retractado: false
  errata: 'JAMA. 2017;318(13):1284.'
  errata_corrige: Incorrect Data.
  errata_verificada: true
  errata_pmid: 'pmid:28973229'
  crossref: true
  crossref_titulo_coincide: false
  notas:
    - 'Tiene errata publicada: comprobar las cifras contra la corrección'
    - 'La errata afecta a DATOS: no transcribir cifras sin cotejarlas'
    - 'Cotejada el 06/09/2026: no toca ningún cociente.'
""")
        claves, notas = generador.conservadas(destino)
        self.assertEqual(claves, {"errata_verificada": True,
                                  "errata_pmid": "pmid:28973229"})
        self.assertEqual(notas, ["Cotejada el 06/09/2026: no toca ningún cociente."])

    def test_descarta_las_notas_de_texto_variable(self):
        """`sin DOI…` y `el DOI no resuelve…` las genera el script con texto propio."""
        destino = self.escribe("""\
verificacion:
  crossref: false
  notas:
    - 'sin DOI en PubMed: la verificación CrossRef no aplica'
    - 'el DOI no resuelve en CrossRef (HTTP 404); PubMed sí lo registra'
    - 'Comprobado a mano contra el número impreso.'
""")
        _, notas = generador.conservadas(destino)
        self.assertEqual(notas, ["Comprobado a mano contra el número impreso."])

    def test_registro_nuevo_no_conserva_nada(self):
        claves, notas = generador.conservadas(Path("/no/existe/pmid-0.yaml"))
        self.assertEqual((claves, notas), ({}, []))

    def test_el_booleano_vuelve_en_minuscula(self):
        """`True` de Python en un YAML del índice sería inconsistente con el resto."""
        self.assertEqual(generador.linea_yaml("errata_verificada", True),
                         "  errata_verificada: true")
        self.assertEqual(generador.linea_yaml("errata_pmid", "pmid:1"),
                         "  errata_pmid: 'pmid:1'")

    def test_los_registros_reales_en_riesgo_siguen_protegidos(self):
        """Los dos que hoy llevan cotejo: si se regeneran, no pueden perderlo."""
        for nombre in ("pmid-28763554.yaml", "pmid-30721300.yaml"):
            with self.subTest(nombre):
                claves, notas = generador.conservadas(RAIZ / "referencias" / nombre)
                self.assertTrue(claves.get("errata_verificada"))
                self.assertTrue(notas, "el rastro del cotejo se perdería")


if __name__ == "__main__":
    unittest.main()
