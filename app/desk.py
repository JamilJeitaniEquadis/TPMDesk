# -*- coding: utf-8 -*-
"""
Pont entre la page et les scripts du skill, exécutés tels quels dans Pyodide.
Chaque fonction publique renvoie du texte court : c'est ce que Claude lit après un appel d'outil.
"""
import io, os, re, sys, json, contextlib
import warnings
warnings.filterwarnings('ignore', message='Workbook contains no default style')
from collections import Counter

sys.path.insert(0, '/skill/scripts')
import pipeline, inspect_export, validate
from openpyxl import load_workbook
from openpyxl.utils import column_index_from_string as cif

EXPORT, TEMPLATE, OUT, REPORT = '/work/export.xlsx', '/work/template.xlsx', '/work/output.xlsx', '/work/log.json'
MAX = 6000
DECISIONS = []          # arbitrages pris pendant la session, rejoués à chaque génération
_paths = None           # liste du champ 11 lue dans l'extraction

def _court(t, n=MAX):
    t = t.rstrip()
    return t if len(t) <= n else t[:n] + f"\n… ({len(t) - n} caractères coupés)"

def _run(module, argv):
    buf = io.StringIO(); code = 0
    old = sys.argv
    sys.argv = [module.__name__ + '.py'] + argv
    try:
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            module.main()
    except SystemExit as e:
        code = e.code if isinstance(e.code, int) else (0 if e.code is None else 1)
    except Exception as e:
        code = 1; buf.write(f"\nERREUR : {type(e).__name__}: {e}")
        import traceback
        pile = [f for f in traceback.extract_tb(e.__traceback__) if '/skill/' in f.filename]
        if pile:
            f = pile[-1]
            buf.write(f"\n   à {os.path.basename(f.filename)}:{f.lineno}  {(f.line or '').strip()[:120]}")
    finally:
        sys.argv = old
    return code, buf.getvalue()

def _need(*paths):
    manque = [p for p in paths if not os.path.exists(p)]
    if manque:
        noms = {EXPORT: "l'export SupplierXM", TEMPLATE: "l'extraction Gaia (gabarit)", OUT: 'le fichier généré'}
        return 'Manquant : ' + ', '.join(noms.get(p, p) for p in manque) + '. Demander à l\'utilisateur de le déposer.'
    return None

def reset_outputs():
    for p in (OUT, REPORT):
        if os.path.exists(p): os.remove(p)

# ---------------------------------------------------------------- reconnaissance
def inspect():
    e = _need(EXPORT)
    if e: return e
    return _court(_run(inspect_export, ['--export', EXPORT])[1])

def products(category, limit=25):
    """Libellés réels des produits d'une catégorie source (code ou libellé)."""
    e = _need(EXPORT)
    if e: return e
    wb = load_workbook(EXPORT, read_only=True, data_only=True)
    P = pipeline.Feuille(wb['Product'])
    q = str(category).strip().lower(); out = []; n = 0
    for r in P.rows:
        kind = str(P.v(r, 'kind') or '')
        if q and q not in kind.lower() and q != pipeline.code(kind).lower(): continue
        n += 1
        if len(out) < int(limit):
            out.append(' | '.join(str(x) for x in [
                P.v(r, 'gtin'), P.v(r, 'namePublicLong'), pipeline.lab(P.v(r, 'isClassifiedIn')),
                pipeline.lab(P.v(r, 'org1337WebsiteProductCategory')),
                pipeline.code(P.v(r, 'targetConsumerGender'))] if x not in (None, '')))
    wb.close()
    if not n: return f"Aucun produit pour la catégorie « {category} »."
    return _court(f"{n} produit(s) — gtin | libellé | classification source | catégorie web | genre\n" + '\n'.join(out))

# ---------------------------------------------------------------- champ 11
def _liste11():
    global _paths
    if _paths is not None: return _paths
    wb = load_workbook(TEMPLATE)
    ws = wb['Produit']
    col = next(c for c in range(1, ws.max_column + 1) if str(ws.cell(row=1, column=c).value) == '11')
    lettre = ws.cell(row=1, column=col).column_letter
    vals = []
    for dv in ws.data_validations.dataValidation:
        cols = {re.match(r'([A-Z]+)', x).group(1) for x in str(dv.sqref).split()}
        if lettre not in cols: continue
        m = re.match(r"(Lists_\w+)!\$([A-Z]+)\$(\d+):\$([A-Z]+)\$(\d+)", str(dv.formula1).strip('='))
        if not m: continue
        w = wb[m.group(1)]; c = cif(m.group(2))
        vals = [str(w.cell(row=r, column=c).value) for r in range(int(m.group(3)), int(m.group(5)) + 1)
                if w.cell(row=r, column=c).value is not None]
        break
    _paths = vals
    return vals

def search_paths(query, limit=40):
    e = _need(TEMPLATE)
    if e: return e
    vals = _liste11()
    if not vals: return "L'extraction ne déclare pas de liste pour le champ 11."
    mots = [m for m in str(query).lower().split() if m]
    hits = [v for v in vals if all(m in v.lower() for m in mots)]
    if not hits and mots:
        hits = [v for v in vals if any(m in v.lower() for m in mots)]
    if not hits: return f"Aucun chemin ne contient « {query} » ({len(vals)} chemins dans la liste)."
    return _court(f"{len(hits)} chemin(s) sur {len(vals)} (copier au caractère près) :\n" +
                  '\n'.join(hits[:int(limit)]))

def set_classification(category, path, reason=''):
    e = _need(TEMPLATE)
    if e: return e
    vals = _liste11()
    if vals and path not in vals:
        proches = [v for v in vals if v.split('|')[-1].strip() == str(path).split('|')[-1].strip()]
        return ("REFUSÉ : ce chemin n'est pas dans la liste du champ 11, il serait rejeté. "
                + ("Entrées avec la même brique :\n" + '\n'.join(proches[:10]) if proches else
                   "Chercher avec search_classification_paths et copier l'entrée exacte."))
    k = pipeline.code(category)
    pipeline.CLASSIF_KIND[k] = path
    DECISIONS[:] = [d for d in DECISIONS if not (d['type'] == 'classification' and d['key'] == k)]
    DECISIONS.append({'type': 'classification', 'key': k, 'value': path, 'reason': reason})
    reset_outputs()
    return f"Catégorie {k} → {path}. Enregistré comme arbitrage à faire valider par le client."

TABLES = {n: getattr(pipeline, n) for n in dir(pipeline) if n.startswith('V_') and isinstance(getattr(pipeline, n), dict)}

def set_value(table, source, target, reason=''):
    t = TABLES.get(str(table))
    if t is None: return f"Table inconnue. Tables : {', '.join(sorted(TABLES))}"
    t[str(source)] = target
    DECISIONS[:] = [d for d in DECISIONS if not (d['type'] == table and d['key'] == source)]
    DECISIONS.append({'type': table, 'key': str(source), 'value': target, 'reason': reason})
    reset_outputs()
    return f"{table}[{source!r}] = {target!r}."

def decisions_json():
    return json.dumps(DECISIONS, ensure_ascii=False)

def restore(js):
    for d in json.loads(js or '[]'):
        if d['type'] == 'classification': pipeline.CLASSIF_KIND[d['key']] = d['value']
        elif d['type'] in TABLES: TABLES[d['type']][d['key']] = d['value']
        DECISIONS.append(d)

# ---------------------------------------------------------------- génération et contrôle
def generate():
    e = _need(EXPORT, TEMPLATE)
    if e: return e
    reset_outputs()
    global _paths
    code, txt = _run(pipeline, ['--export', EXPORT, '--template', TEMPLATE, '--out', OUT, '--report', REPORT])
    if code or not os.path.exists(OUT):
        return _court('ÉCHEC de la génération.\n' + txt + '\n\n' + diagnostic())
    return _court(txt + ("\n\nArbitrages appliqués : " + str(len(DECISIONS)) if DECISIONS else ''))

def check():
    e = _need(OUT, TEMPLATE)
    if e: return e
    code, txt = _run(validate, ['--file', OUT, '--template', TEMPLATE])
    return _court(('CODE RETOUR 0 — déposable\n' if code == 0 else f'CODE RETOUR {code} — non déposable\n') + txt)

def anomalies(limit=60):
    if not os.path.exists(REPORT): return 'Pas de journal : lancer la génération.'
    log = json.load(open(REPORT, encoding='utf-8'))
    c = Counter(x['champ'] for x in log)
    lignes = [f"{len(log)} anomalies. Par champ :"] + [f"  {v:4}  {k}" for k, v in c.most_common(20)]
    lignes += ['', 'Détail :'] + [f"  {x['gtin']} | {x['champ']} | {x['constat']}" for x in log[:int(limit)]]
    return _court('\n'.join(lignes))

def read_reference(name):
    n = re.sub(r'[^a-z\-]', '', str(name).lower())
    p = f'/skill/references/{n}.md'
    if not os.path.exists(p):
        return 'Références : ' + ', '.join(sorted(f[:-3] for f in os.listdir('/skill/references')))
    return _court(open(p, encoding='utf-8').read(), 9000)

def new_template():
    global _paths
    _paths = None
    reset_outputs()

def diagnostic():
    """Contrôle du gabarit sur les points où l'écriture XML de pipeline.py suppose un fichier issu de Gaia."""
    import zipfile
    e = _need(TEMPLATE)
    if e: return e
    L = ['Diagnostic de l\'extraction :']
    try:
        z = zipfile.ZipFile(TEMPLATE)
    except Exception as x:
        return f"L'extraction n'est pas un .xlsx lisible ({x})."
    noms = set(z.namelist())
    app = z.read('docProps/app.xml').decode('utf-8', 'replace') if 'docProps/app.xml' in noms else ''
    m = re.search(r'<Application>([^<]*)</Application>', app)
    L.append(f"- Application inscrite dans le fichier : {m.group(1) if m else 'aucune'} "
             "(une extraction ouverte puis enregistrée dans Excel n'est plus déposable)")
    if 'xl/sharedStrings.xml' not in noms:
        L.append("- sharedStrings.xml absent : le fichier n'est pas une extraction Gaia brute.")
    else:
        ss = z.read('xl/sharedStrings.xml').decode('utf-8', 'replace')
        ok = re.search(r'<sst count="(\d+)" uniqueCount="(\d+)"', ss)
        L.append("- En-tête sharedStrings : " + ("conforme" if ok else
                 "NON CONFORME (" + (re.findall(r'<sst[^>]*>', ss) or [''])[0][:140]
                 + ") : attendu <sst count=\"…\" uniqueCount=\"…\" en premier, comme l'écrit Gaia."))
    wb = z.read('xl/workbook.xml').decode('utf-8', 'replace')
    ordre = re.findall(r'<sheet [^>]*name="([^"]+)"', wb)
    L.append(f"- Onglets : {', '.join(ordre[:8])}")
    for i, nom in enumerate(('Produit', 'Logistique'), 1):
        f = f'xl/worksheets/sheet{i}.xml'
        if f not in noms:
            L.append(f"- {f} absent."); continue
        xml = z.read(f).decode('utf-8', 'replace')
        lignes = [int(x) for x in re.findall(r'<row r="(\d+)"', xml)]
        der = max(lignes) if lignes else 0
        a_16 = pipeline.LAST_TPL in lignes
        L.append(f"- {f} (attendu : {nom}) : lignes jusqu'à {der}, ligne {pipeline.LAST_TPL} "
                 + ("présente" if a_16 else f"ABSENTE -> au-delà de {pipeline.LAST_TPL - pipeline.FIRST_NEW + 1} produits, "
                    "pipeline.py ne trouve pas de ligne modèle à dupliquer"))
    L.append("Une extraction faite dans Gaia et déposée telle quelle passe ces contrôles. Sinon, refaire "
             "l'extraction depuis Gaia et la déposer sans l'ouvrir dans Excel.")
    if ordre[:2] != ['Produit', 'Logistique']:
        L.append("- Les deux premiers onglets ne sont pas Produit puis Logistique : pipeline.py écrit dans sheet1/sheet2.")
    return '\n'.join(L)

# ---------------------------------------------------------------- bac à sable
_NS = None

def run_python(code):
    """Exécute du Python dans la page, comme l'outil d'exécution de code d'une conversation Claude.
    L'espace de noms persiste d'un appel à l'autre ; pipeline, inspect_export, validate et desk y sont importés."""
    global _NS
    if _NS is None:
        _NS = {'__name__': '__sandbox__', 'pipeline': pipeline, 'inspect_export': inspect_export,
               'validate': validate, 'desk': sys.modules[__name__], 'EXPORT': EXPORT, 'TEMPLATE': TEMPLATE,
               'OUT': OUT, 'REPORT': REPORT}
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            import ast
            arbre = ast.parse(code, '<claude>')
            fin = arbre.body.pop() if arbre.body and isinstance(arbre.body[-1], ast.Expr) else None
            exec(compile(arbre, '<claude>', 'exec'), _NS)
            if fin is not None:
                v = eval(compile(ast.Expression(fin.value), '<claude>', 'eval'), _NS)
                if v is not None: print(repr(v))
    except SystemExit as e:
        buf.write(f"\n(SystemExit {e.code})")
    except Exception:
        import traceback
        buf.write(traceback.format_exc(limit=6))
    out = buf.getvalue() or '(aucune sortie)'
    return _court(out, 8000)

def output_ready():
    return os.path.exists(OUT)

def template_ok():
    """'' si l'extraction a la forme qu'attend pipeline.py, sinon la raison en une ligne."""
    import zipfile
    try:
        z = zipfile.ZipFile(TEMPLATE)
        wb = z.read('xl/workbook.xml').decode('utf-8', 'replace')
        ss = z.read('xl/sharedStrings.xml').decode('utf-8', 'replace')[:600]
    except Exception:
        return "ce n'est pas une extraction Gaia (fichier ou parties manquantes)"
    ordre = re.findall(r'<sheet [^>]*name="([^"]+)"', wb)
    if ordre[:2] != ['Produit', 'Logistique']:
        return f"onglets {', '.join(ordre[:3])} : Produit et Logistique doivent être les deux premiers"
    if not re.search(r'<sst count="\d+" uniqueCount="\d+"', ss):
        return "fichier ré-enregistré dans Excel (en-tête sharedStrings modifié), Gaia le refusera"
    for i in (1, 2):
        xml = z.read(f'xl/worksheets/sheet{i}.xml').decode('utf-8', 'replace')
        if f'<row r="{pipeline.LAST_TPL}"' not in xml:
            return f"ligne modèle {pipeline.LAST_TPL} absente de l'onglet {ordre[i-1]}"
    return ''
