# Visualizing the AI Economy

A Quarto dashboard project for **DATASCI 209** at UC Berkeley MIDS. We're using Quarto's `dashboard` format with Python (Altair, pandas, itables) to visualize public data on the AI economy — starting with Epoch AI's frontier data centers dataset.

> **Working title.** The project name may change; the deploy URL and repo will stay the same.

## Stack at a glance

- **Quarto** — website project, with `index.qmd` rendered using `format: dashboard`
- **Python** — Altair + pandas for charts, itables for interactive tables
- **Posit Connect Cloud** — auto-deploys from `main`

**Live dashboard:** <https://019e8093-0783-ce2c-6773-7172db1a16e9.share.connect.posit.cloud>

## Quick start

You'll need [Quarto](https://quarto.org/docs/get-started/) (≥ 1.4) and Python 3.11+ installed.

```bash
git clone https://github.com/rpuncel/datasci-209-proj.git
cd datasci-209-proj

python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

quarto preview                     # live-reload preview at http://localhost:<port>
```

To produce the static build under `_site/`:

```bash
quarto render
```

You can then open `_site/index.html` in your web browser to view the static site.

## Editing the dashboard

The dashboard homepage is [`index.qmd`](./index.qmd). If you're coming from `.Rmd`/RStudio, the YAML front matter and fenced Python chunks will feel familiar — the main thing that's new is that **headings are layout**: `#` defines a dashboard page, `##` defines a row/column of cards, and cell options like `#| title:` or `#| content: valuebox` control how a chunk renders.

See [`docs/authoring.md`](./docs/authoring.md) for a 5-minute walkthrough that maps `index.qmd` line-by-line to what you see in the browser.

## IDE setup

**Recommended: [Positron](https://positron.posit.co/)** — Posit's data science IDE (built on VS Code) with first-class Quarto and Python support, and an interaction model that feels close to RStudio.

VS Code also works fine with the right extensions. Step-by-step setup for both editors is in [`docs/ide-setup.md`](./docs/ide-setup.md).

## Workflow
 
### Suggested Workflow

1. Branch from `main` (`git checkout -b your-name/new-section`).
2. Edit the relevant `.qmd`. Keep `quarto preview` running — it hot-reloads on save.
3. Commit, push, open a PR. Have a teammate review if desired - use your judgement on whether your changes could break something or not.
4. **Merge to `main` → Posit Connect Cloud re-renders and deploys automatically.** The update should be live in no longer than 5 minutes.

If you're adding a whole new analysis page, create a new `.qmd` and add it to `_quarto.yml`'s `navbar`.

### The exploratory report (PDF + DOCX)

`exploratory-report.qmd` declares `format: [html, typst, docx]`, so `quarto render` produces the HTML page plus a PDF (Quarto's bundled Typst engine) and a DOCX. Connect Cloud runs the same render on deploy, so **the PDF/DOCX build server-side — there's nothing to pre-build, copy, or commit.** Just edit the `.qmd`; the "Other Formats" links on the report page serve the freshly rendered files. (Both artifacts are gitignored.)

## Deployment

`main` is the live branch. Posit Connect Cloud is connected to this GitHub repo, watches `main`, and re-renders the site on every merge — pulling deps from `requirements.txt`. **Don't deploy manually.** If a deploy fails, check the Connect Cloud logs (ask Rob for access).

If you add a new Python dependency, install it into `.venv` and run `pip freeze > requirements.txt` so Connect Cloud picks it up.

## Quarto bookmarks

These four are the ones you'll actually want open while authoring:

- [Dashboards overview](https://quarto.org/docs/dashboards/) — get an overall idea of how we're using Quarto.
- [Dashboard layout](https://quarto.org/docs/dashboards/layout.html) — pages, rows, columns, tabsets
- [Dashboard data display](https://quarto.org/docs/dashboards/data-display.html) — value boxes, plots, tables, text
- [Python code cells](https://quarto.org/docs/computations/python.html) — chunk options that Python folks need

For `.Rmd` veterans: [Migrating from R Markdown](https://quarto.org/docs/faq/rmarkdown.html) is a useful diff.

## Repo layout

```
index.qmd                    # the dashboard homepage
exploratory-report.qmd       # EDA report — renders to HTML + PDF (typst) + DOCX
about.qmd                    # placeholder "About" page
_quarto.yml                  # site + render config
requirements.txt             # Python deps (used by local venv AND Connect Cloud)
references.bib               # bibliography
styles.css                   # global site CSS
docs/                        # this README's companion docs (not part of the deployed site)
data/                        # downloaded datasets (gitignored — fetched at render time)
_site/                       # rendered static output (gitignored)
```

## We'll evolve as we collaborate

The project structure may evolve as we collaborate, and we may learn some initial setup doesn't work well. 
We'll aim to do what works and evolve as we go; reach out over our Slack if you have some pain points.

## Acknowledgements

This project uses data from the following sources. We appreciate the work these organizations have done,
and strive to appropriately give them credit and follow their license terms.

- Epoch AI - provides curated data sets about data centers progress, usage, and more under [Creative Commons V4](https://creativecommons.org/licenses/by/4.0/).
  - See their work [here](https://epoch.ai/data)