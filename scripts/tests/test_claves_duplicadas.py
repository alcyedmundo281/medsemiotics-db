"""Regresión: una clave repetida en un registro no se pierde en silencio.

PyYAML se queda con la última aparición de una clave. Así perdió HM:3030 su
procedencia real —un segundo bloque `procedencia` añadido después la
sustituyó— y así habría perdido HM:6009 su primer `pendiente`. build.py tiene
que rechazarlo, en cualquier nivel del registro.

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


class ClavesDuplicadasTest(unittest.TestCase):
    def setUp(self):
        temporal = tempfile.TemporaryDirectory()
        self.addCleanup(temporal.cleanup)
        self.raiz = Path(temporal.name)
        (self.raiz / "scripts").mkdir()
        shutil.copy2(RAIZ / "scripts" / "build.py", self.raiz / "scripts" / "build.py")
        for carpeta in ("conceptos", "condiciones", "referencias"):
            (self.raiz / carpeta).mkdir()

    def valida(self, concepto):
        (self.raiz / "conceptos" / "HM3001.yaml").write_text(concepto, encoding="utf8")
        hecho = subprocess.run(
            [sys.executable, str(self.raiz / "scripts" / "build.py")],
            capture_output=True, text=True, encoding="utf8",
        )
        return hecho.returncode, hecho.stdout + hecho.stderr

    def test_clave_repetida_en_el_primer_nivel_falla(self):
        codigo, salida = self.valida(
            CONCEPTO + "procedencia: {fuente: una}\nprocedencia: {fuente: otra}\n")
        self.assertEqual(codigo, 1, salida)
        self.assertIn("repetida", salida)

    def test_clave_repetida_anidada_falla(self):
        codigo, salida = self.valida(
            CONCEPTO + "procedencia:\n  fuente: una\n  fuente: otra\n")
        self.assertEqual(codigo, 1, salida)

    def test_registro_sin_repetidas_pasa(self):
        codigo, salida = self.valida(CONCEPTO + "procedencia: {fuente: una}\n")
        self.assertEqual(codigo, 0, salida)


if __name__ == "__main__":
    unittest.main()
