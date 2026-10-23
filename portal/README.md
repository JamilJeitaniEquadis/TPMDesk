# TPM Portal

The TPM Desk stays on Jamil's machine. Some of its features are **modules** that can also be published
on a public web portal (GitHub Pages), for other project managers.

```
portal/
  modules/<id>/          one module = one folder: module.json + index.html (+ its scripts)
  build_portal.py        builds portal/dist/ from the modules listed in portal.config.json, checks it, publishes it
  portal.config.json     YOUR settings, on your machine only (not committed)
  portal.config.example.json
```

## Modules

| Module | What it does |
|---|---|
| `project-planner` | One standard plan for every project: roles, phases, tasks with R/A/C/I and dates, checks that nothing is missing, then an Excel with the sheets the PM picks: Scope, RACI, Tracker (counts, overdue, days left) and Gantt. The DSA POC template starts with Scope, Tracker and Gantt. The Excel keeps the plan in a hidden sheet, so it can be reopened and updated. |

A module must work on its own: no server, no login, nothing sent anywhere, no client data inside it.
In the desk, `app/build.py` embeds each module as one HTML file (sidebar: **Project planner**).

## Project archive

The plans are kept as Excel files in the team's SharePoint folder (one file per project, SharePoint keeps
every version). In the desk opened with **Open desk.bat**, the planner's **My projects** card uses that folder
synced on the laptop (SharePoint: **Sync** or **Add shortcut to My files**): it lists every project with its
progress, opens one to continue it, and **Save to archive** writes it back to the same file. The folder is
chosen once and kept in `app/desk.settings.json` (not committed). On the public portal the card only offers
the SharePoint folder link and **Open a saved plan**.

## Publishing (Jamil only)

1. Once: `copy portal\portal.config.example.json portal\portal.config.json` (public repository: https://github.com/JamilJeitaniEquadis/tpm-portal). Commits use the GitHub noreply address set in `commit_email`, never the work address.
2. In the desk opened with **Open desk.bat**, a **Portal** page appears at the bottom of the sidebar (only on
   a machine that has `portal.config.json`). Tick the modules to publish, then **Build and check** or
   **Publish to the portal**. Or from a terminal: `python portal/build_portal.py --push`.
3. Every published file is scanned for the `block_words` (client names, `@equadis.com`, server paths...).
   One hit stops the publish.

GitHub Pages serves the public repository: https://jamiljeitaniequadis.github.io/tpm-portal/

## Later: an interface for the clients' project managers (idea, not built)

Once the planner is used internally and proves efficient, give the clients' project managers their own
access, so both sides fill in the same plan:

- a client user sees only their projects, and updates the status of the tasks where their side is R;
- the Equadis PM keeps the structure (phases, dates, RACI) and validates the changes;
- the exported RACI / Gantt stays the shared reference.

This needs what a static GitHub Pages site cannot do: accounts and logins, projects stored on a server,
rights per client. So it belongs in the Equadis project manager portal (to discuss with the CTO), with the
planner's plan format (`v: 1` JSON: project, roles, phases, tasks) as the data model to keep.
