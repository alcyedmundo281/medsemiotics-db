"""Vuelve a generar, contra PubMed, las referencias cuya errata está sin comprobar.

    python scripts/9_desbloquear_referencias.py            # las regenera
    python scripts/9_desbloquear_referencias.py --listar   # solo dice cuáles
    python scripts/9_desbloquear_referencias.py --pausa 2  # más lento

POR QUÉ EXISTE. Una referencia puede entrar en el índice sin que nadie haya
podido mirar si el artículo tiene errata publicada: pasó con las 59 que trajo la
oleada 1, importadas desde una red que no alcanzaba eutils. Esas llevan
`errata_comprobada: false`, y build.py FALLA en cuanto una de ellas sostiene un
cociente o un umbral. El candado es deliberado: un registro sin campo `errata`
es indistinguible de uno que se comprobó y salió limpio, y esa diferencia es
justo la que se pierde sola.

QUÉ HACE. Busca las que llevan el candado y llama a
`scripts/6_referencia_por_pmid.py` sobre cada una. Ese script sí consulta
PubMed, sí detecta la errata y tiene `errata_comprobada` en CLAVES_GENERADAS,
así que al regenerar el registro BORRA el campo. El candado se abre solo.

NO SUSTITUYE A `8_comprobar_erratas.py`, que informa sobre TODAS las referencias
y no escribe nada. Éste escribe, y solo sobre las que están bloqueadas.

DÓNDE CORRERLO. Donde `eutils.ncbi.nlm.nih.gov` responda. No sirve una sesión
cuya política de egreso lo bloquee, que es la razón de que estas referencias
entraran con candado; por eso lo primero que hace es comprobar la conexión y
parar con un mensaje claro en vez de soltar 59 trazas seguidas.

ES RE-EJECUTABLE. No lleva lista fija: descubre las pendientes en cada corrida,
así que si alguna falla basta con volver a lanzarlo y solo reintenta ésas.
"""
import argparse, pathlib, subprocess, sys, time, urllib.error, urllib.request

try:
    import yaml
except ImportError:
    sys.exit('Falta PyYAML:  pip install pyyaml')

RAIZ = pathlib.Path(__file__).resolve().parent.parent
SCRIPT6 = RAIZ / 'scripts' / '6_referencia_por_pmid.py'
SONDA = ('https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi'
         '?db=pubmed&id=27115266&retmode=json')


def pendientes():
    """Las que declaran que nadie ha mirado su errata."""
    fuera = []
    for f in sorted((RAIZ / 'referencias').glob('*.yaml')):
        d = yaml.safe_load(f.read_text(encoding='utf8')) or {}
        v = d.get('verificacion') or {}
        if v.get('errata_comprobada') is False:
            pmid = (d.get('identificadores') or {}).get('pmid')
            clave = d.get('clave_bibtex')
            if not pmid or not clave:
                print(f'  ⚠ {f.name}: lleva el candado pero le falta '
                      f'{"pmid" if not pmid else "clave_bibtex"}; se salta')
                continue
            fuera.append((f, str(pmid), clave))
    return fuera


def hay_pubmed():
    try:
        with urllib.request.urlopen(SONDA, timeout=30):
            return True
    except Exception as e:
        print('NO SE ALCANZA PUBMED, y sin PubMed este script no puede hacer nada.')
        print(f'  {type(e).__name__}: {e}')
        print('\nEs exactamente la situación que hizo entrar estas referencias con')
        print('candado. Corre esto desde una red que alcance eutils.ncbi.nlm.nih.gov.')
        return False


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--listar', action='store_true',
                   help='solo enumera las pendientes; no toca nada ni consulta PubMed')
    p.add_argument('--pausa', type=float, default=1.0,
                   help='segundos entre referencias (PubMed admite 3 peticiones por '
                        'segundo sin clave y el script 6 hace varias; por defecto 1.0)')
    a = p.parse_args()

    cola = pendientes()
    if not cola:
        print('No hay ninguna referencia con la errata sin comprobar. Nada que hacer.')
        return 0

    print(f'referencias con la errata sin comprobar: {len(cola)}')
    if a.listar:
        for f, pmid, clave in cola:
            print(f'  {pmid:>9}  {clave:22} {f.name}')
        print('\nPara regenerarlas:  python scripts/9_desbloquear_referencias.py')
        return 0

    if not hay_pubmed():
        return 2

    fallidas, con_errata = [], []
    for i, (f, pmid, clave) in enumerate(cola, 1):
        print(f'\n[{i}/{len(cola)}] pmid:{pmid}  {clave}')
        r = subprocess.run([sys.executable, str(SCRIPT6), pmid, clave],
                           capture_output=True, text=True)
        if r.returncode != 0:
            # Una que falle no puede llevarse por delante a las otras 58.
            print(f'  ✗ falló: {(r.stderr or r.stdout).strip().splitlines()[-1:] or ["sin salida"]}')
            fallidas.append((pmid, clave))
        else:
            d = yaml.safe_load(f.read_text(encoding='utf8')) or {}
            v = d.get('verificacion') or {}
            if v.get('errata_comprobada') is False:
                print('  ✗ el candado sigue puesto: revisa CLAVES_GENERADAS del script 6')
                fallidas.append((pmid, clave))
            elif v.get('errata'):
                print(f'  ⚠ TIENE ERRATA: {v["errata"]}')
                con_errata.append((pmid, clave, v['errata']))
            else:
                print('  ✓ comprobada, sin errata')
        if i < len(cola):
            time.sleep(a.pausa)

    print(f'\n{"="*70}\ndesbloqueadas {len(cola) - len(fallidas)} de {len(cola)}')
    if con_errata:
        print(f'\n⚠ CON ERRATA PUBLICADA ({len(con_errata)}) — cotéjala antes de que '
              f'sostengan ninguna cifra:')
        for pmid, clave, err in con_errata:
            print(f'    pmid:{pmid}  {clave}\n        {err}')
    if fallidas:
        print(f'\n✗ FALLARON {len(fallidas)}; vuelve a lanzar el script y lo reintenta:')
        for pmid, clave in fallidas:
            print(f'    {pmid}  {clave}')
        return 1
    print('\nAhora corre  python scripts/build.py')
    return 0


if __name__ == '__main__':
    sys.exit(main())
