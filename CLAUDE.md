# Visualizing the AI Economy

A Quarto dashboard project for **DATASCI 209** at UC Berkeley MIDS. Visualizes public data on the AI economy using Epoch AI's frontier data centers dataset.

**Live dashboard:** <https://019e8093-0783-ce2c-6773-7172db1a16e9.share.connect.posit.cloud>

## Stack

- **Quarto** — website project; `index.qmd` rendered with `format: dashboard`
- **Python** — Altair + pandas for charts, itables for interactive tables
- **Posit Connect Cloud** — auto-deploys from `main` on every merge

## Key commands

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
quarto preview      # live-reload preview
quarto render       # static build → _site/
```

## Repo layout

```
index.qmd           # dashboard homepage (main editing target)
about.qmd           # placeholder About page
_quarto.yml         # Quarto site + render config
requirements.txt    # Python deps (used by .venv AND Connect Cloud)
styles.css          # global CSS
data/               # downloaded datasets (gitignored — fetched at render time)
docs/               # companion docs (authoring.md, ide-setup.md)
_site/              # rendered static output (gitignored)
.scratch/           # local issue tracker (gitignored)
```

## Deployment

`main` is the live branch. Posit Connect Cloud watches it and re-renders on every merge. **Do not deploy manually.** If a deploy fails, check the Connect Cloud logs.

When adding a Python dependency: install into `.venv`, then `pip freeze > requirements.txt`.

## Quarto dashboard layout rules

In Quarto dashboard format, headings are layout — not section titles:
- `#` — defines a dashboard page
- `##` — defines a row or column of cards
- Cell option `#| title:` or `#| content: valuebox` controls how a chunk renders

## Agent skills

### Issue tracker

Issues live as local markdown files under `.scratch/`. See `docs/agents/issue-tracker.md`.

### Triage labels

Default five-role vocabulary (needs-triage, needs-info, ready-for-agent, ready-for-human, wontfix). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context repo — one `CONTEXT.md` at the root, `docs/adr/` for decisions. See `docs/agents/domain.md`.

### Project skills

- **`/quarto-authoring`** — use when working with `.qmd` files, code cell options, cross-references, figures, tables, citations, or `_quarto.yml` config (general Quarto; does not cover dashboard-specific layout)
- **`/alt-text`** — use when adding or editing charts or images; generates accessible alt-text for visualizations
- **`/brand-yml`** — use when configuring or updating visual brand/theming in `_brand.yml`
