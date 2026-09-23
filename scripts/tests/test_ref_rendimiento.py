"""Regresión: una sensibilidad o especificidad no entra sin procedencia.

Un LR sin `ref` era error desde el principio, pero el rendimiento de una arista
`no_medido` —sensibilidad sin especificidad, o al revés— no llevaba ningún LR
que cargara la ref, y el número entraba sin fuente sin que nada saltara. Había
cinco así en el índice.

La `ref` de la arista no siempre sirve: en HM:6001 la ictericia la usa para
sostener la `decision` con otra fuente. Por eso el rendimiento tiene su propia
clave, `ref_rendimiento`, que además queda bajo el candado de la errata.

Se ejecuta el `build.py` real como subproceso sobre un índice mínimo.
"""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]

CONCEPTO = """\
id: 'HM:3001'
tipo: concepto
semantica: hallazgo
termino: Hallazgo de prueba
significante: hay
"""


def referencia(pmid, verificacion="{pubmed: true}"):
    return f"""\
id: 'pmid:{pmid}'
clave_bibtex: prueba{pmid}
titulo: Fuente {pmid}
identificadores: {{pmid: '{pmid}'}}
verificacion: {verificacion}
"""


def condicion(arista):
    return f"""\
id: 'HM:6001'
tipo: condicion
clase: enfermedad
termino: Condición de prueba
signos:
  - concepto: 'HM:3001'
    estado_lr: no_medido
{arista}"""


class RefRendimientoTest(unittest.TestCase):
    def setUp(self):
        temporal = tempfile.TemporaryDirectory()
        self.addCleanup(temporal.cleanup)
        self.raiz = Path(temporal.name)
        (self.raiz / "scripts").mkdir()
        shutil.copy2(RAIZ / "scripts" / "build.py", self.raiz / "scripts" / "build.py")
        for carpeta in ("conceptos", "condiciones", "referencias"):
            (self.raiz / carpeta).mkdir()

    def valida(self, arista, referencias=None):
        referencias = referencias or {1: referencia(1), 2: referencia(2)}
        (self.raiz / "conceptos" / "HM3001.yaml").write_text(CONCEPTO, encoding="utf8")
        (self.raiz / "condiciones" / "HM6001.yaml").write_text(
            condicion(arista), encoding="utf8")
        for pmid, texto in referencias.items():
            (self.raiz / "referencias" / f"pmid-{pmid}.yaml").write_text(
                texto, encoding="utf8")
        hecho = subprocess.run(
            [sys.executable, str(self.raiz / "scripts" / "build.py")],
            capture_output=True, text=True, encoding="utf8",
        )
        return hecho.returncode, hecho.stdout + hecho.stderr

    # ── la regla muerde ───────────────────────────────────────────────────────

    def test_sensibilidad_sin_ninguna_ref_falla(self):
        codigo, salida = self.valida("    sensibilidad: 0.6\n")
        self.assertEqual(codigo, 1, salida)
        self.assertIn("sin procedencia", salida)

    def test_especificidad_sin_ninguna_ref_falla(self):
        codigo, salida = self.valida("    especificidad: 0.98\n")
        self.assertEqual(codigo, 1, salida)

    def test_ref_rendimiento_que_no_resuelve_falla(self):
        codigo, salida = self.valida(
            "    sensibilidad: 0.6\n    ref_rendimiento: 'pmid:9'\n")
        self.assertEqual(codigo, 1, salida)
        self.assertIn("pmid:9", salida)

    def test_ref_rendimiento_sin_rendimiento_falla(self):
        """Una fuente que no sostiene ningún número es una cita colgada."""
        codigo, salida = self.valida("    ref_rendimiento: 'pmid:1'\n")
        self.assertEqual(codigo, 1, salida)

    def test_ref_rendimiento_queda_bajo_el_candado_de_la_errata(self):
        """Si el barrido de erratas no la viera, citaría una fuente sin cotejar."""
        codigo, salida = self.valida(
            "    sensibilidad: 0.6\n    ref_rendimiento: 'pmid:1'\n",
            {1: referencia(1, "{pubmed: true, errata_comprobada: false}")},
        )
        self.assertEqual(codigo, 1, salida)
        self.assertIn("ERRATA ESTÁ SIN COMPROBAR", salida)

    # ── y no muerde de más ────────────────────────────────────────────────────

    def test_ref_rendimiento_distinta_de_la_ref_de_la_decision(self):
        """El caso de la ictericia: dos fuentes, cada una para lo suyo."""
        codigo, salida = self.valida(
            "    decision: orienta\n    ref: 'pmid:1'\n"
            "    sensibilidad: 0.667\n    ref_rendimiento: 'pmid:2'\n")
        self.assertEqual(codigo, 0, salida)

    def test_la_ref_de_la_arista_sigue_valiendo(self):
        """Compatibilidad: las aristas con una sola fuente no necesitan la clave."""
        codigo, salida = self.valida(
            "    sensibilidad: 0.33\n    ref: 'pmid:1'\n")
        self.assertEqual(codigo, 0, salida)


if __name__ == "__main__":
    unittest.main()
