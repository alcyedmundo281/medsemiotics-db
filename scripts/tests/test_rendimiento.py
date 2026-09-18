"""Regresiones de la línea «Rendimiento»: sensibilidad y especificidad con su IC95.

Antes el punto salía con `:.0%` y el intervalo tal cual venía del YAML, así que
el libro publicaba «Se 99% (IC95% 0.953–0.998)»: dos unidades en la misma frase
y una estimación de 98.7% redondeada a 99%. El índice es la autoridad; el libro
no puede publicar ni más ni menos precisión que la que guarda.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import banco


class PorcentajeTest(unittest.TestCase):
    def test_conserva_los_decimales_del_indice(self):
        self.assertEqual(banco.porcentaje(0.987, "Se"), "Se 98.7%")
        self.assertEqual(banco.porcentaje(0.76, "Se"), "Se 76%")
        self.assertEqual(banco.porcentaje(0.6, "Sp"), "Sp 60%")
        self.assertEqual(banco.porcentaje(1.0, "Sp"), "Sp 100%")
        self.assertEqual(banco.porcentaje(0.07, "Se"), "Se 7%")

    def test_el_intervalo_va_en_la_misma_unidad_que_el_punto(self):
        self.assertEqual(banco.porcentaje(0.987, "Se", [0.953, 0.998]),
                         "Se 98.7% (IC95% 95.3%–99.8%)")
        self.assertEqual(banco.porcentaje(0.76, "Se", [0.6, 0.87]),
                         "Se 76% (IC95% 60%–87%)")
        self.assertEqual(banco.porcentaje(0.98, "Sp", [0.96, 1.00]),
                         "Sp 98% (IC95% 96%–100%)")

    def test_texto_se_publica_tal_cual(self):
        self.assertEqual(banco.porcentaje("alta", "Se"), "Se alta")
        self.assertEqual(banco.porcentaje("alta", "Se", ["a", "b"]),
                         "Se alta (IC95% a–b)")


class RendimientoEnAristaTest(unittest.TestCase):
    def test_nota_de_rendimiento(self):
        indice = banco.Indice.__new__(banco.Indice)
        indice.conceptos = {"HM:3001": dict(termino="Hallazgo", id="HM:3001")}
        indice.condiciones_por_archivo = {}
        indice.referencias = {}
        arista = dict(concepto="HM:3001", estado_lr="no_medido",
                      sensibilidad=0.987, ic95_sensibilidad=[0.953, 0.998],
                      especificidad=0.76, ic95_especificidad=[0.6, 0.87])
        _, notas = banco.filas_de_signo(indice, arista, "prueba")
        self.assertIn(
            ("Hallazgo — Rendimiento",
             "Se 98.7% (IC95% 95.3%–99.8%), Sp 76% (IC95% 60%–87%)."),
            notas,
        )


if __name__ == "__main__":
    unittest.main()
