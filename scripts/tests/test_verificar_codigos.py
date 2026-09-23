"""Regresiones del verificador de códigos y del registro de búsquedas.

El verificador se prueba sin red: se le inyectan las respuestas de la OMS y de
tx.fhir.org que se observaron el 2026-09-23. Así el test no se vuelve inestable
por un fallo de red, y a la vez fija el formato de respuesta del que depende.

El caso real que motivó el script: HM:6045 declaraba CIE-10 I31.4 y SNOMED
42232009, y ninguno de los dos existe en las fuentes que el índice cita.
"""
import importlib.util
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location(
    "verificar_codigos", RAIZ / "scripts" / "10_verificar_codigos.py")
vc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(vc)

OMS = {
    "B17.9": {"ID": "B17.9", "label": "B17.9 Acute viral hepatitis, unspecified", "isLeaf": True},
    "K58": {"ID": "K58", "label": "K58 Irritable bowel syndrome", "isLeaf": False},
    "I31.4": None,
}
SNOMED = {
    "57412004": {"resourceType": "Parameters", "parameter": [
        {"name": "version", "valueString": "http://snomed.info/sct/900000000000207008/version/20250201"},
        {"name": "display", "valueString": "Acute viral hepatitis"},
        {"name": "designation", "part": [{"name": "value", "valueString": "Acute viral hepatitis (disorder)"}]},
        {"name": "property", "part": [{"name": "code", "valueCode": "inactive"},
                                      {"name": "value", "valueBoolean": False}]},
        {"name": "property", "part": [{"name": "code", "valueCode": "module"},
                                      {"name": "value", "valueCode": "900000000000207008"}]},
    ]},
    "42232009": {"resourceType": "OperationOutcome", "issue": [{"code": "not-found"}]},
}


def falso(url, fhir=False):
    codigo = url.split("ConceptId=")[1].split("&")[0] if "ConceptId=" in url \
        else url.split("code=")[1].split("&")[0]
    return (SNOMED if fhir else OMS).get(codigo)


def registro(cie10=None, snomed=None, termino_en="Acute viral hepatitis"):
    return {"id": "HM:6001", "tipo": "condicion", "termino_en": termino_en,
            "codigos": {"cie10": cie10, "snomed": snomed}}


class VerificarCodigosTest(unittest.TestCase):
    def test_codigos_reales_pasan(self):
        informe, errores, avisos = vc.comprobar(registro("B17.9", "57412004"), falso)
        self.assertEqual(errores, [])
        self.assertEqual(avisos, [])
        self.assertIn("Acute viral hepatitis (disorder)", " ".join(informe))

    def test_codigos_inexistentes_son_error(self):
        """El caso de HM:6045: dos códigos escritos de memoria."""
        _, errores, _ = vc.comprobar(registro("I31.4", "42232009"), falso)
        self.assertEqual(len(errores), 2)
        self.assertIn("I31.4", errores[0])
        self.assertIn("42232009", errores[1])

    def test_categoria_es_aviso_no_error(self):
        _, errores, avisos = vc.comprobar(
            registro("K58", termino_en="Irritable bowel syndrome"), falso)
        self.assertEqual(errores, [])
        self.assertTrue(any("categoría" in a for a in avisos))

    def test_etiqueta_sin_relacion_con_el_termino_avisa(self):
        _, _, avisos = vc.comprobar(registro("B17.9", termino_en="Cardiac tamponade"), falso)
        self.assertTrue(any("no comparte" in a for a in avisos))

    def test_variantes_ortograficas_no_avisan(self):
        """«goitre» en la OMS y «goiter» en la ficha son la misma palabra."""
        self.assertTrue(vc.palabras("Nontoxic goitre, unspecified") & vc.palabras("Goiter"))


class BusquedaReproducibleTest(unittest.TestCase):
    def setUp(self):
        temporal = tempfile.TemporaryDirectory()
        self.addCleanup(temporal.cleanup)
        self.raiz = Path(temporal.name)
        (self.raiz / "scripts").mkdir()
        shutil.copy2(RAIZ / "scripts" / "build.py", self.raiz / "scripts" / "build.py")
        for carpeta in ("conceptos", "condiciones", "referencias"):
            (self.raiz / carpeta).mkdir()

    def valida(self, nota):
        (self.raiz / "condiciones" / "HM6001.yaml").write_text(
            "id: 'HM:6001'\ntipo: condicion\nclase: enfermedad\ntermino: Prueba\n"
            f"pendiente:\n  - >-\n    {nota}\n", encoding="utf8")
        hecho = subprocess.run(
            [sys.executable, str(self.raiz / "scripts" / "build.py")],
            capture_output=True, text=True, encoding="utf8")
        return hecho.stdout + hecho.stderr

    def test_busqueda_sin_consulta_avisa(self):
        salida = self.valida("Búsqueda en PubMed del 2026-09-21: no se hallaron estudios.")
        self.assertIn("no reproducible", salida)
        self.assertIn("consulta", salida)

    def test_busqueda_completa_no_avisa(self):
        salida = self.valida(
            "Búsqueda en PubMed del 2026-09-23. Consulta «hepatitis[Title]»: "
            "98 resultados, cribados por título.")
        self.assertNotIn("no reproducible", salida)


if __name__ == "__main__":
    unittest.main()
