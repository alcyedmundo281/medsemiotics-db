"""Regresión del candado: una referencia sin cotejar su errata no sostiene nada.

Una referencia puede entrar en el índice sin que nadie haya podido mirar si el
artículo tiene errata publicada —pasó con las 59 de la oleada 1, importadas
desde una red que no alcanzaba eutils—. El peligro no es el hueco sino su
forma: un registro SIN campo `errata` es indistinguible de uno que se comprobó
y salió limpio, así que 59 referencias sin verificar parecerían verificadas en
la capa que sostiene todas las cifras del índice.

`errata_comprobada: false` dice «nadie ha mirado», no «no tiene». Mientras nadie
la cite es un aviso; en cuanto sostiene un cociente o un umbral, build.py falla.

Se ejecuta el `build.py` real como subproceso sobre un índice mínimo: validar
contra una copia de las reglas dejaría de probar las reglas.
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

CONCEPTO_CON_UMBRAL = """\
id: 'HM:3001'
tipo: concepto
semantica: hallazgo
termino: Hallazgo de prueba
significante: hay
umbral:
  parametro: Hallazgo
  unidad: mm
  direccion: alto
  corte_superior: 3
  ref: 'pmid:1'
"""

SIN_COMPROBAR = """\
id: 'pmid:1'
clave_bibtex: prueba2026
titulo: Fuente sin cotejar
identificadores: {pmid: '1'}
verificacion: {pubmed: true, errata_comprobada: false}
"""

COMPROBADA = """\
id: 'pmid:1'
clave_bibtex: prueba2026
titulo: Fuente cotejada
identificadores: {pmid: '1'}
verificacion: {pubmed: true}
"""

CONDICION_SUELTA = """\
id: 'HM:6001'
tipo: condicion
clase: enfermedad
termino: Condición de prueba
"""

CONDICION_QUE_CITA = """\
id: 'HM:6001'
tipo: condicion
clase: enfermedad
termino: Condición de prueba
signos:
  - concepto: 'HM:3001'
    estado_lr: medido
    lr_positivo: {valor: 4.2, ref: 'pmid:1'}
"""


class ErrataSinComprobarTest(unittest.TestCase):
    def setUp(self):
        temporal = tempfile.TemporaryDirectory()
        self.addCleanup(temporal.cleanup)
        self.raiz = Path(temporal.name)
        (self.raiz / "scripts").mkdir()
        shutil.copy2(RAIZ / "scripts" / "build.py", self.raiz / "scripts" / "build.py")
        for carpeta in ("conceptos", "condiciones", "referencias"):
            (self.raiz / carpeta).mkdir()

    def valida(self, referencia, condicion, concepto=CONCEPTO):
        (self.raiz / "conceptos" / "HM3001.yaml").write_text(concepto, encoding="utf8")
        (self.raiz / "condiciones" / "HM6001.yaml").write_text(condicion, encoding="utf8")
        (self.raiz / "referencias" / "pmid-1.yaml").write_text(referencia, encoding="utf8")
        hecho = subprocess.run(
            [sys.executable, str(self.raiz / "scripts" / "build.py")],
            # `encoding` explícito, no solo `text=True`: sin él Python decodifica
            # la salida del subproceso con la codificación del SISTEMA —cp1252 en
            # Windows— y build.py imprime «», ⚠ y acentos. El test entonces falla
            # en la máquina del autor y pasa en CI, que es el peor reparto
            # posible: rompe el comando que documenta CLAUDE.md justo para quien
            # lo va a correr a diario.
            capture_output=True, text=True, encoding="utf8",
        )
        return hecho.returncode, hecho.stdout + hecho.stderr

    # ── el candado muerde ─────────────────────────────────────────────────────

    def test_falla_si_sostiene_un_cociente(self):
        """Es la razón de existir del campo: sin cotejar no mueve una probabilidad."""
        codigo, salida = self.valida(SIN_COMPROBAR, CONDICION_QUE_CITA)
        self.assertEqual(codigo, 1, f"debería haber fallado:\n{salida}")
        self.assertIn("ERRATA ESTÁ SIN COMPROBAR", salida)

    def test_falla_si_sostiene_un_umbral(self):
        """Un umbral es un dato tan citable como un cociente, y cambia decisiones."""
        codigo, salida = self.valida(
            SIN_COMPROBAR, CONDICION_SUELTA, concepto=CONCEPTO_CON_UMBRAL)
        self.assertEqual(codigo, 1, f"debería haber fallado:\n{salida}")
        self.assertIn("ERRATA ESTÁ SIN COMPROBAR", salida)

    def test_el_error_dice_como_arreglarlo(self):
        """Un candado que no nombra su llave se convierte en un misterio."""
        _, salida = self.valida(SIN_COMPROBAR, CONDICION_QUE_CITA)
        self.assertIn("6_referencia_por_pmid.py 1 prueba2026", salida)

    # ── y no muerde de más ────────────────────────────────────────────────────

    def test_sin_citar_solo_avisa(self):
        """Importar una referencia por adelantado es legítimo; usarla a ciegas no."""
        codigo, salida = self.valida(SIN_COMPROBAR, CONDICION_SUELTA)
        self.assertEqual(codigo, 0, salida)

    def test_una_referencia_ya_cotejada_puede_sostener_lo_que_sea(self):
        """Sin el campo, el registro pasó por el script 6 y su errata está mirada."""
        codigo, salida = self.valida(COMPROBADA, CONDICION_QUE_CITA)
        self.assertEqual(codigo, 0, salida)


if __name__ == "__main__":
    unittest.main()
