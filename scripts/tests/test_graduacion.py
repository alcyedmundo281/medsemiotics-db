"""Regresiones del eje de graduación: tramos con límites legibles por máquina.

Cada caso protege una lectura silenciosamente equivocada de un valor de
laboratorio, que es la única razón por la que el eje existe. Se ejecuta el
`build.py` real como subproceso sobre un índice mínimo: validar contra una copia
de las reglas dejaría de probar las reglas en cuanto una de las dos cambiara.
"""
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]

CONCEPTO = """\
id: 'HM:3001'
tipo: concepto
semantica: hallazgo
termino: Hallazgo graduado
significante: hay
"""

REFERENCIA = """\
id: 'pmid:1'
titulo: Fuente de prueba
identificadores: {pmid: '1'}
verificacion: {pubmed: true}
"""

CONDICION = """\
id: 'HM:6001'
tipo: condicion
clase: enfermedad
termino: Condición de prueba
signos:
{signos}
"""


class GraduacionTest(unittest.TestCase):
    def setUp(self):
        temporal = tempfile.TemporaryDirectory()
        self.addCleanup(temporal.cleanup)
        self.raiz = Path(temporal.name)
        (self.raiz / "scripts").mkdir()
        shutil.copy2(RAIZ / "scripts" / "build.py", self.raiz / "scripts" / "build.py")
        for carpeta, nombre, texto in (
            ("conceptos", "HM3001.yaml", CONCEPTO),
            ("referencias", "pmid-1.yaml", REFERENCIA),
        ):
            (self.raiz / carpeta).mkdir()
            (self.raiz / carpeta / nombre).write_text(texto, encoding="utf8")
        (self.raiz / "condiciones").mkdir()

    def valida(self, signos, concepto=CONCEPTO):
        """Escribe el índice mínimo, corre build.py y devuelve (codigo, salida)."""
        (self.raiz / "conceptos" / "HM3001.yaml").write_text(concepto, encoding="utf8")
        (self.raiz / "condiciones" / "HM6001.yaml").write_text(
            CONDICION.format(signos=textwrap.indent(textwrap.dedent(signos), "  ")),
            encoding="utf8",
        )
        hecho = subprocess.run(
            [sys.executable, str(self.raiz / "scripts" / "build.py")],
            capture_output=True, text=True,
        )
        return hecho.returncode, hecho.stdout + hecho.stderr

    def acepta(self, signos, concepto=CONCEPTO):
        codigo, salida = self.valida(signos, concepto)
        self.assertEqual(codigo, 0, salida)

    def rechaza(self, signos, fragmento, concepto=CONCEPTO):
        codigo, salida = self.valida(signos, concepto)
        self.assertEqual(codigo, 1, f"debería haber fallado:\n{salida}")
        self.assertIn(fragmento, salida)

    # ── lo que tiene que pasar ────────────────────────────────────────────────

    def test_acumulativo_valido(self):
        """Cortes anidados: se solapan a propósito y no son un error."""
        self.acepta("""
            - concepto: 'HM:3001'
              estado_lr: medido
              lr_positivo: {valor: 11.4, ref: 'pmid:1'}
              graduacion: {parametro: Hallazgo, unidad: '%', lectura: acumulativo}
              tramos:
                - {umbral: '≥ 10%', desde: 10, lr_positivo: 11.4, ref: 'pmid:1'}
                - {umbral: '≥ 20%', desde: 20, lr_positivo: 26, ref: 'pmid:1'}
        """)

    def test_disjunto_valido_sin_cubrir_toda_la_recta(self):
        """Los tramos no tienen que cubrir todo: el hueco es la respuesta honesta."""
        self.acepta("""
            - concepto: 'HM:3001'
              estado_lr: medido
              lr_positivo: {valor: 13, ref: 'pmid:1'}
              graduacion: {parametro: Puntuación, unidad: puntos, lectura: disjunto}
              tramos:
                - {umbral: '0 a 3', desde: 0, hasta: 4, lr_positivo: 0.2, ref: 'pmid:1'}
                - {umbral: '7 a 10', desde: 7, hasta: 11, lr_positivo: 13, ref: 'pmid:1'}
        """)

    def test_tramo_en_prosa_sigue_valiendo(self):
        """La compatibilidad hacia atrás: un tramo sin límites no exige graduación."""
        self.acepta("""
            - concepto: 'HM:3001'
              estado_lr: medido
              lr_positivo: {valor: 54, ref: 'pmid:1'}
              tramos:
                - {umbral: 'linfocitos > 50% y atípicos > 10%', lr_positivo: 54, ref: 'pmid:1'}
        """)

    def test_poblaciones_distintas_pueden_solaparse(self):
        """El corte de varón y el de mujer se solapan por definición."""
        self.acepta("""
            - concepto: 'HM:3001'
              estado_lr: medido
              lr_positivo: {valor: 3, ref: 'pmid:1'}
              graduacion: {parametro: Creatinina, unidad: mg/dL, lectura: disjunto}
              tramos:
                - {umbral: 'varón', desde: 1.3, poblacion: varones, lr_positivo: 3, ref: 'pmid:1'}
                - {umbral: 'mujer', desde: 1.1, poblacion: mujeres, lr_positivo: 3, ref: 'pmid:1'}
        """)

    # ── lo que no puede pasar ─────────────────────────────────────────────────

    def test_limites_sin_graduacion(self):
        self.rechaza("""
            - concepto: 'HM:3001'
              estado_lr: medido
              lr_positivo: {valor: 11.4, ref: 'pmid:1'}
              tramos:
                - {umbral: '≥ 10%', desde: 10, lr_positivo: 11.4, ref: 'pmid:1'}
        """, "falta «graduacion»")

    def test_graduacion_sin_unidad(self):
        self.rechaza("""
            - concepto: 'HM:3001'
              estado_lr: medido
              lr_positivo: {valor: 11.4, ref: 'pmid:1'}
              graduacion: {parametro: Hallazgo, lectura: acumulativo}
              tramos:
                - {umbral: '≥ 10', desde: 10, lr_positivo: 11.4, ref: 'pmid:1'}
        """, "graduacion sin «unidad»")

    def test_lectura_no_se_infiere(self):
        self.rechaza("""
            - concepto: 'HM:3001'
              estado_lr: medido
              lr_positivo: {valor: 11.4, ref: 'pmid:1'}
              graduacion: {parametro: Hallazgo, unidad: '%'}
              tramos:
                - {umbral: '≥ 10%', desde: 10, lr_positivo: 11.4, ref: 'pmid:1'}
        """, "fuera de la taxonomía")

    def test_disjuntos_que_se_solapan(self):
        self.rechaza("""
            - concepto: 'HM:3001'
              estado_lr: medido
              lr_positivo: {valor: 3, ref: 'pmid:1'}
              graduacion: {parametro: Potasio, unidad: mmol/L, lectura: disjunto}
              tramos:
                - {umbral: 'a', desde: 3.0, hasta: 3.6, lr_positivo: 2.4, ref: 'pmid:1'}
                - {umbral: 'b', desde: 3.5, hasta: 4.0, lr_positivo: 1.2, ref: 'pmid:1'}
        """, "se solapan")

    def test_acumulativo_con_los_dos_extremos(self):
        self.rechaza("""
            - concepto: 'HM:3001'
              estado_lr: medido
              lr_positivo: {valor: 3, ref: 'pmid:1'}
              graduacion: {parametro: Hallazgo, unidad: '%', lectura: acumulativo}
              tramos:
                - {umbral: 'a', desde: 10, hasta: 20, lr_positivo: 3, ref: 'pmid:1'}
        """, "un solo lado")

    def test_acumulativo_repite_corte(self):
        self.rechaza("""
            - concepto: 'HM:3001'
              estado_lr: medido
              lr_positivo: {valor: 3, ref: 'pmid:1'}
              graduacion: {parametro: Hallazgo, unidad: '%', lectura: acumulativo}
              tramos:
                - {umbral: 'a', desde: 10, lr_positivo: 3, ref: 'pmid:1'}
                - {umbral: 'b', desde: 10, lr_positivo: 9, ref: 'pmid:1'}
        """, "aparece en dos tramos")

    def test_intervalo_vacio(self):
        self.rechaza("""
            - concepto: 'HM:3001'
              estado_lr: medido
              lr_positivo: {valor: 3, ref: 'pmid:1'}
              graduacion: {parametro: Hallazgo, unidad: '%', lectura: disjunto}
              tramos:
                - {umbral: 'a', desde: 20, hasta: 10, lr_positivo: 3, ref: 'pmid:1'}
        """, "no es menor que")

    def test_no_se_mezclan_los_dos_ejes(self):
        """Graduar el hallazgo y redefinir la condición no son el mismo eje."""
        self.rechaza("""
            - concepto: 'HM:3001'
              estado_lr: medido
              lr_positivo: {valor: 12, ref: 'pmid:1'}
              graduacion: {parametro: Diámetro, unidad: cm, lectura: acumulativo}
              tramos:
                - {umbral_condicion: '≥ 3 cm', desde: 3, lr_positivo: 12, ref: 'pmid:1'}
                - {umbral: '≥ 4 cm', desde: 4, lr_positivo: 15.6, ref: 'pmid:1'}
        """, "mezclan «umbral» y «umbral_condicion»")

    def test_graduacion_sin_efecto(self):
        self.rechaza("""
            - concepto: 'HM:3001'
              estado_lr: medido
              lr_positivo: {valor: 3, ref: 'pmid:1'}
              graduacion: {parametro: Hallazgo, unidad: '%', lectura: acumulativo}
              tramos:
                - {umbral: 'a', lr_positivo: 3, ref: 'pmid:1'}
        """, "ningún tramo trae")

    def test_lr_negativo_sin_declarar_su_corte(self):
        """«Negativa» tiene que estar definido con precisión o no descarta nada."""
        self.rechaza("""
            - concepto: 'HM:3001'
              estado_lr: medido
              lr_positivo: {valor: 12, ref: 'pmid:1'}
              lr_negativo: {valor: 0.1, ref: 'pmid:1'}
              graduacion: {parametro: Hallazgo, unidad: xLSN, lectura: acumulativo}
              tramos:
                - {umbral: '≥ 3x', desde: 3, lr_positivo: 12, ref: 'pmid:1'}
        """, "qué corte define «negativo»")

    def test_unidad_contradice_al_concepto(self):
        """La unidad canónica vive en el concepto; la arista la comprueba."""
        concepto = CONCEPTO + textwrap.dedent("""\
            umbral:
              parametro: Hallazgo graduado
              unidad: mmol/L
              corte_superior: 5.5
              ref: 'pmid:1'
            """)
        self.rechaza("""
            - concepto: 'HM:3001'
              estado_lr: medido
              lr_positivo: {valor: 3, ref: 'pmid:1'}
              graduacion: {parametro: Hallazgo graduado, unidad: mg/dL, lectura: acumulativo}
              tramos:
                - {umbral: 'a', desde: 6, lr_positivo: 3, ref: 'pmid:1'}
        """, "contradice el umbral del concepto", concepto=concepto)


class TextoGraduacionTest(unittest.TestCase):
    """El libro tiene que publicar los límites, no sólo la prosa que ya traía."""

    def setUp(self):
        sys.path.insert(0, str(RAIZ / "scripts"))
        global banco
        import banco

    def test_intervalo_semiabierto_explicito(self):
        self.assertEqual(
            banco.intervalo_texto({"desde": 7, "hasta": 11}, "puntos"),
            "≥ 7 y < 11 puntos",
        )
        self.assertEqual(banco.intervalo_texto({"desde": 10}, "%"), "≥ 10 %")
        self.assertEqual(banco.intervalo_texto({"hasta": 3}, "puntos"), "< 3 puntos")
        self.assertEqual(banco.intervalo_texto({"umbral": "en prosa"}), "")

    def test_la_nota_dice_como_se_leen_los_tramos(self):
        texto = banco.nota_graduacion({
            "graduacion": {"parametro": "Lipasa", "unidad": "xLSN",
                           "lectura": "acumulativo"},
            "tramos": [{"desde": 3}, {"desde": 10}],
        })
        self.assertIn("Lipasa (xLSN)", texto)
        self.assertIn("más estricto", texto)
        self.assertIn("≥ 3; ≥ 10", texto)

    def test_sin_graduacion_no_hay_nota(self):
        self.assertEqual(banco.nota_graduacion({"tramos": [{"umbral": "x"}]}), "")


if __name__ == "__main__":
    unittest.main()
