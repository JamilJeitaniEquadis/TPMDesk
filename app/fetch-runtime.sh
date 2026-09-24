#!/usr/bin/env sh
# Rebuild app/py/ : Pyodide 0.26.4 + openpyxl, needed to publish tpm-desk.html.
# The artifact host does not serve .zip, so the archives get a .wasm suffix (bytes unchanged).
set -e
cd "$(dirname "$0")"
tmp=$(mktemp -d)
(cd "$tmp" && npm pack pyodide@0.26.4 --silent >/dev/null && tar xzf pyodide-0.26.4.tgz)
mkdir -p py
for f in pyodide.js pyodide.asm.js pyodide.asm.wasm pyodide-lock.json; do cp "$tmp/package/$f" py/; done
cp "$tmp/package/python_stdlib.zip" py/python_stdlib.zip.wasm
pip download openpyxl==3.1.5 et_xmlfile==2.0.0 --no-deps -d "$tmp/w" -q
for w in "$tmp"/w/*.whl; do cp "$w" "py/$(basename "$w").wasm"; done
rm -rf "$tmp"
ls -la py
