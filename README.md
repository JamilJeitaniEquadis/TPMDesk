# TPM Desk

`app/tpm-desk.html` is the Technical Project Manager Desk (Excel → Equa Excel), published as a claude.ai artifact.

Step 2 runs the `marionnaud-gaia-migration` skill in the page. The skill's own scripts (`app/skill/`) run
unchanged in Pyodide. Claude, through the artifact `sample` capability, calls them as tools (`app/desk.py`):
inspect the export, list products in a category, search the extraction's field 11 paths, set a
classification or a list value, generate, validate. The Inspect / Generate / Validate buttons run the
same functions without Claude. The generated file is saved with the `downloads` capability or handed to step 3.

The skill, `desk.py` and the openpyxl wheels are embedded in the HTML (`#bundle` block), so the page also
works as a local file: it then loads the Pyodide core from cdn.jsdelivr.net (internet needed) and the buttons
run the pipeline. The Claude chat only works in the page published on claude.ai.

When the skill or `desk.py` changes: copy the skill's `SKILL.md`, `scripts/`, `references/` and `assets/` into
`app/skill/`, run `app/fetch-runtime.sh` once (rebuilds `app/py/`), then `python app/build.py`, and republish
`app/tpm-desk.html` with the `py/*` files attached and capabilities `{sample: {}, downloads: true}`.
