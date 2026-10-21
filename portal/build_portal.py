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
    title = html.escape(conf.get('site_title', 'TPM Portal'))
    cards = '\n'.join(
        f'<a class="card" href="{html.escape(m["id"])}/{html.escape(m.get("entry", "index.html"))}">'
        f'<b>{html.escape(m["name"])}</b><span>{html.escape(m.get("description", ""))}</span>'
        f'<em>{html.escape(m.get("audience", ""))} · v{html.escape(m.get("version", "1"))}</em></a>' for m in mods)
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
:root{{--paper:#EDF0F3;--card:#F8FAFB;--ink:#112032;--soft:#5A6B7C;--rule:#C7D0D8;--accent:#58EA9D}}
@media (prefers-color-scheme:dark){{:root{{--paper:#0C1620;--card:#14222F;--ink:#E4ECF2;--soft:#8FA2B3;--rule:#24384B}}}}
*{{box-sizing:border-box}} body{{margin:0;background:var(--paper);color:var(--ink);font:15px/1.55 Archivo,system-ui,-apple-system,"Segoe UI",sans-serif}}
main{{max-width:960px;margin:0 auto;padding:40px 16px 64px}} h1{{font-size:clamp(28px,4vw,38px);margin:0 0 6px;letter-spacing:-.5px}}
p{{color:var(--soft);margin:0 0 26px}} .grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(280px,100%),1fr));gap:14px}}
.card{{display:flex;flex-direction:column;gap:6px;padding:18px 20px;border:1px solid var(--rule);border-radius:12px;background:var(--card);color:inherit;text-decoration:none}}
.card:hover,.card:focus-visible{{border-color:var(--accent);outline:none}} .card b{{font-size:17px}} .card span{{color:var(--soft)}} .card em{{font-style:normal;font-size:12.5px;color:var(--soft)}}
footer{{margin-top:40px;font-size:12.5px;color:var(--soft)}}
</style></head>
<body><main><h1>{title}</h1><p>{html.escape(conf.get("site_intro", "Tools for project managers. Everything runs in your browser: nothing you type is sent anywhere."))}</p>
<div class="grid">
{cards}
</div><footer>Built from the TPM Desk.</footer></main></body></html>
'''


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


def git(*args, cwd=PUBLIC):
    subprocess.run(['git', *args], cwd=cwd, check=True)


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
    git('commit', '-m', 'Publish: ' + ', '.join(f'{m["name"]} {m.get("version", "")}'.strip() for m in chosen))
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
