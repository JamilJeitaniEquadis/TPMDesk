# -*- coding: utf-8 -*-
"""TPM Portal: builds the public web portal from the modules you choose to publish.

    python portal/build_portal.py            build portal/dist/ and check it
    python portal/build_portal.py --push     ...then publish it to the public repository

What gets published is decided by portal/portal.config.json, which stays on your machine (it is
never committed: see portal.config.example.json). Each module is a folder in portal/modules/
with a module.json; it is copied as it is. Before anything leaves the machine, every published
file is scanned for the words listed in "block_words" (client names, internal addresses, server
paths...): one hit stops the publish.

--push clones the public repository next to this script (portal/.public/), replaces its content
with dist/, commits and pushes with your own git login. GitHub Pages then serves it.
"""
import argparse
import html
import json
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MODULES = os.path.join(HERE, 'modules')
DIST = os.path.join(HERE, 'dist')
PUBLIC = os.path.join(HERE, '.public')
CONFIG = os.path.join(HERE, 'portal.config.json')
TEXT = ('.html', '.js', '.css', '.json', '.md', '.txt', '.svg')


def modules() -> dict:
    out = {}
    for name in sorted(os.listdir(MODULES)):
        meta = os.path.join(MODULES, name, 'module.json')
        if os.path.exists(meta):
            m = json.load(open(meta, encoding='utf-8'))
            out[m['id']] = dict(m, folder=os.path.join(MODULES, name))
    return out


def load_config() -> dict:
    if not os.path.exists(CONFIG):
        raise SystemExit('No portal/portal.config.json on this machine: copy portal.config.example.json to it first.')
    return json.load(open(CONFIG, encoding='utf-8'))


def inline(folder: str, entry: str = 'index.html') -> str:
    """The module as one HTML file: each <script src="x"> replaced by its content (for the desk)."""
    page = open(os.path.join(folder, entry), encoding='utf-8').read()

    def repl(m):
        src = os.path.join(folder, m.group(1))
        code = open(src, encoding='utf-8').read().replace('</script', '<\\/script')
        return '<script>' + code + '</script>'
    return re.sub(r'<script src="([^":]+)"></script>', repl, page)


def home(conf: dict, mods: list) -> str:
    """The portal shell: the desk's left sidebar (brand, one entry per module) and the module in a frame."""
    e = html.escape
    title, sub = e(conf.get('site_title', 'Project Manager Desk')), e(conf.get('site_subtitle', 'Tools for project managers'))
    intro = e(conf.get('site_intro', 'Tools for project managers. Everything runs in your browser: nothing you type is sent anywhere.'))
    nav = '\n'.join(f'<a class="mod" href="#{e(m["id"])}" data-id="{e(m["id"])}" data-src="{e(m["id"])}/{e(m.get("entry", "index.html"))}">{e(m["name"])}</a>' for m in mods)
    cards = '\n'.join(f'<a class="card" href="#{e(m["id"])}"><b>{e(m["name"])}</b><span>{e(m.get("description", ""))}</span>'
                      f'<em>{e(m.get("audience", ""))} · v{e(m.get("version", "1"))}</em></a>' for m in mods)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
:root{{--primary:#112032;--accent:#58EA9D;--paper:#EDF0F3;--card:#F8FAFB;--ink:#112032;--soft:#5A6B7C;--rule:#C7D0D8;--rail:#112032;--rail-ink:#D7E2EA}}
@media (prefers-color-scheme:dark){{:root:not([data-theme="light"]){{--paper:#0C1620;--card:#14222F;--ink:#E4ECF2;--soft:#8FA2B3;--rule:#24384B;--rail:#0A121B;--rail-ink:#CFDCE6}}}}
:root[data-theme="dark"]{{--paper:#0C1620;--card:#14222F;--ink:#E4ECF2;--soft:#8FA2B3;--rule:#24384B;--rail:#0A121B;--rail-ink:#CFDCE6}}
*{{box-sizing:border-box}} html,body{{height:100%}}
body{{margin:0;background:var(--paper);color:var(--ink);font:15px/1.55 Archivo,system-ui,-apple-system,"Segoe UI",sans-serif;display:flex}}
.rail{{width:224px;flex:0 0 224px;background:var(--rail);color:var(--rail-ink);display:flex;flex-direction:column;height:100vh;position:sticky;top:0}}
.brand{{padding:22px 20px 16px;border-bottom:1px solid rgba(255,255,255,.12);color:inherit;text-decoration:none}}
.brand b{{display:block;font-size:16px;font-weight:700;color:#fff;letter-spacing:-.2px}} .brand span{{display:block;font-size:12.5px;color:var(--accent);margin-top:3px;font-weight:500}}
nav{{padding:12px 8px;flex:1;overflow-y:auto}}
nav .lbl{{font-size:11.5px;letter-spacing:.6px;text-transform:uppercase;color:#7E8A95;padding:6px 12px 4px}}
nav a{{display:block;color:var(--rail-ink);text-decoration:none;font-weight:600;font-size:14.5px;padding:9px 12px;border-radius:8px;border-left:3px solid transparent;margin:2px 0}}
nav a:hover{{background:rgba(255,255,255,.08)}} nav a[aria-current="page"]{{background:rgba(88,234,157,.14);border-left-color:var(--accent);color:#fff}}
nav a:focus-visible,.foot button:focus-visible{{outline:2px solid var(--accent);outline-offset:2px}}
.foot{{padding:12px 16px 20px;font-size:12px;color:#7E8A95;border-top:1px solid rgba(255,255,255,.12)}}
.foot button{{font:inherit;background:none;border:0;padding:0;color:#7E8A95;text-decoration:underline;cursor:pointer}}
main{{flex:1;min-width:0;height:100vh;overflow:auto}}
#frame{{display:block;width:100%;height:100vh;border:0}}
.home{{max-width:960px;margin:0 auto;padding:40px 24px 64px}} h1{{font-size:clamp(28px,4vw,36px);margin:0 0 6px;letter-spacing:-.5px}}
.home p{{color:var(--soft);margin:0 0 26px;max-width:70ch}} .grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(280px,100%),1fr));gap:14px}}
.card{{display:flex;flex-direction:column;gap:6px;padding:18px 20px;border:1px solid var(--rule);border-radius:12px;background:var(--card);color:inherit;text-decoration:none}}
.card:hover,.card:focus-visible{{border-color:var(--accent);outline:none}} .card b{{font-size:17px}} .card span{{color:var(--soft)}} .card em{{font-style:normal;font-size:12.5px;color:var(--soft)}}
[hidden]{{display:none!important}}
@media(max-width:860px){{
  body{{flex-direction:column}} .rail{{width:auto;flex:none;height:auto;position:sticky;top:0;z-index:5;padding:10px 12px 8px}}
  .brand{{border:0;padding:0 0 8px}} .brand span,.foot,nav .lbl{{display:none}}
  nav{{display:flex;gap:6px;padding:0;overflow-x:auto}} nav a{{white-space:nowrap;padding:7px 12px;font-size:13.5px;border:1px solid rgba(255,255,255,.14);margin:0}}
  main{{height:auto;overflow:visible}} #frame{{height:calc(100vh - 96px)}} .home{{padding:22px 16px 48px}}
}}
</style></head>
<body>
<aside class="rail">
  <a class="brand" href="#"><b>{title}</b><span>{sub}</span></a>
  <nav aria-label="Modules"><a href="#" data-id="" aria-current="page">Home</a><div class="lbl">Modules</div>
{nav}
  </nav>
  <div class="foot">Runs in your browser: nothing is sent anywhere.<br><button id="theme">Switch theme</button></div>
</aside>
<main>
  <section class="home" id="home"><h1>{title}</h1><p>{intro}</p><div class="grid">
{cards}
  </div></section>
  <iframe id="frame" title="Module" hidden></iframe>
</main>
<script>
(function(){{
  var frame=document.getElementById('frame'), home=document.getElementById('home');
  function show(){{
    var id=location.hash.slice(1), a=id && document.querySelector('nav a.mod[data-id="'+id+'"]');
    document.querySelectorAll('nav a').forEach(function(x){{ x.setAttribute('aria-current', (a ? x===a : x.dataset.id==='') ? 'page' : 'false'); }});
    if(a){{ if(frame.getAttribute('src')!==a.dataset.src) frame.src=a.dataset.src; frame.title=a.textContent; frame.hidden=false; home.hidden=true; document.title=a.textContent+' · {title}'; }}
    else {{ frame.hidden=true; home.hidden=false; document.title='{title}'; }}
  }}
  window.addEventListener('hashchange', show); show();
  var root=document.documentElement;
  try{{ var t=localStorage.getItem('pmd-theme'); if(t) root.setAttribute('data-theme',t); }}catch(e){{}}
  document.getElementById('theme').onclick=function(){{
    var cur=root.getAttribute('data-theme'), dark=cur ? cur==='dark' : matchMedia('(prefers-color-scheme:dark)').matches;
    root.setAttribute('data-theme', dark?'light':'dark'); try{{ localStorage.setItem('pmd-theme', dark?'light':'dark'); }}catch(e){{}}
  }};
}})();
</script>
</body></html>
"""


def build(conf: dict) -> list:
    mods = modules()
    wanted = conf.get('publish', [])
    unknown = [m for m in wanted if m not in mods]
    if unknown:
        raise SystemExit('Unknown module(s) in portal.config.json: ' + ', '.join(unknown))
    if not wanted:
        raise SystemExit('Nothing to publish: add module ids to "publish" in portal.config.json.')
    shutil.rmtree(DIST, ignore_errors=True)
    os.makedirs(DIST)
    chosen = [mods[m] for m in wanted]
    for m in chosen:
        shutil.copytree(m['folder'], os.path.join(DIST, m['id']), ignore=shutil.ignore_patterns('*.py', '__pycache__', 'test*'))
    open(os.path.join(DIST, 'index.html'), 'w', encoding='utf-8').write(home(conf, chosen))
    open(os.path.join(DIST, '.nojekyll'), 'w').close()
    open(os.path.join(DIST, 'README.md'), 'w', encoding='utf-8').write(
        f'# {conf.get("site_title", "TPM Portal")}\n\nStatic web tools for project managers, served by GitHub Pages.\n\n'
        + '\n'.join(f'- **{m["name"]}** (`{m["id"]}/`): {m.get("description", "")}' for m in chosen)
        + '\n\nThis repository is generated: changes are made in the source project and published from there.\n')
    return chosen


def scan(conf: dict) -> list:
    """Every published text file, checked for the words that must never go public."""
    words = [w for w in conf.get('block_words', []) if w.strip()]
    hits = []
    for root, _, files in os.walk(DIST):
        for f in files:
            if not f.endswith(TEXT) or f.endswith('.min.js'):
                continue
            path = os.path.join(root, f)
            text = open(path, encoding='utf-8', errors='replace').read().lower()
            hits += [(os.path.relpath(path, DIST), w) for w in words          # whole words: "ELC" is not "welcome"
                     if re.search(r'(?<![\w])' + re.escape(w.lower()) + r'(?![\w])', text)]
    return hits


def git(*args):
    subprocess.run(['git', *args], cwd=PUBLIC, check=True)


def push(conf: dict, chosen: list):
    repo, branch = conf.get('public_repo'), conf.get('branch', 'main')
    if not repo:
        raise SystemExit('Set "public_repo" in portal.config.json (the public repository to publish to).')
    if not os.path.isdir(os.path.join(PUBLIC, '.git')):
        shutil.rmtree(PUBLIC, ignore_errors=True)
        subprocess.run(['git', 'clone', repo, PUBLIC], check=True)
    git('fetch', 'origin')
    r = subprocess.run(['git', 'rev-parse', '--verify', 'origin/' + branch], cwd=PUBLIC, capture_output=True)
    git('checkout', '-B', branch, *(['origin/' + branch] if r.returncode == 0 else []))
    for name in os.listdir(PUBLIC):
        if name != '.git':
            p = os.path.join(PUBLIC, name)
            shutil.rmtree(p) if os.path.isdir(p) else os.remove(p)
    shutil.copytree(DIST, PUBLIC, dirs_exist_ok=True)
    git('add', '-A')
    if subprocess.run(['git', 'diff', '--cached', '--quiet'], cwd=PUBLIC).returncode == 0:
        print('The public portal is already up to date.')
        return
    # The public history shows the author: never the work address, always the GitHub "noreply" one from the config.
    who = ['-c', 'user.name=' + conf.get('commit_name', 'TPM Portal'),
           '-c', 'user.email=' + conf.get('commit_email', 'noreply@users.noreply.github.com')]
    git(*who, 'commit', '-m', 'Publish: ' + ', '.join(f'{m["name"]} {m.get("version", "")}'.strip() for m in chosen))
    git('push', 'origin', branch)
    print('Published to', repo)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--push', action='store_true', help='publish to the public repository after the build')
    ap.add_argument('--pause', action='store_true', help='wait for Enter at the end (started from the desk)')
    a = ap.parse_args(argv)
    try:
        run(a)
    finally:
        if a.pause:
            input('\nPress Enter to close this window.')


def run(a):
    conf = load_config()
    chosen = build(conf)
    print('Built portal/dist with:', ', '.join(m['name'] for m in chosen))
    hits = scan(conf)
    if hits:
        print('\nNOT PUBLISHED: these files contain words listed in block_words:')
        for f, w in hits:
            print(f'  {f}: "{w}"')
        raise SystemExit(1)
    print('Checked: no blocked word in the published files.')
    if a.push:
        push(conf, chosen)


if __name__ == '__main__':
    if sys.platform == 'win32':
        sys.stdout.reconfigure(encoding='utf-8')
    main()
