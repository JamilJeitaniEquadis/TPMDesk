# TPM Desk

`app/tpm-desk.html` is the Technical Project Manager Desk (Excel → Equa Excel), published as a claude.ai artifact.

Step 2 runs the `marionnaud-gaia-migration` skill in the page. The skill's own scripts (`app/skill/`) run
unchanged in Pyodide. Claude, through the artifact `sample` capability, calls them as tools (`app/desk.py`):
inspect the export, list products in a category, search the extraction's field 11 paths, set a
classification or a list value, generate, validate. The Inspect / Generate / Validate buttons run the
same functions without Claude. The generated file is saved with the `downloads` capability or handed to step 3.

To publish: run `app/fetch-runtime.sh` to rebuild `app/py/`, then publish `app/tpm-desk.html` with
`desk.py`, `py/*` and `skill/**` as supporting files and capabilities `{sample: {}, downloads: true}`.
When the skill changes, copy its `SKILL.md`, `scripts/`, `references/` and `assets/` into `app/skill/` and republish.
