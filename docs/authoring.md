# Authoring the dashboard

A 5-minute tour of how `index.qmd` maps to the rendered dashboard, so you can add new sections without trial-and-error.

If you've used `.Rmd`, **the chunk syntax is identical** — fenced ``` ```{python} ``` ``` blocks, `#|` cell options. What's new is that **Quarto's `dashboard` format treats headings as layout instructions**, not just text.

## The front matter

```yaml
---
title: "Visualizing the AI Economy"
format: dashboard
---
```

`format: dashboard` is what turns the file from "a webpage with code chunks" into a multi-tab dashboard with rows, columns, and cards. See the [Quarto dashboards docs](https://quarto.org/docs/dashboards/) for the full set of front-matter options.

## How headings become layout

| Markdown | What it renders as |
| --- | --- |
| `# Heading 1` | A **page** (top-level tab in the dashboard's navbar) |
| `## Heading 2` | A **row** or **column** within the current page |
| `### Heading 3` | A nested row/column within that |

In our `index.qmd` today:

- `# Overview` → the first tab
- `# Data center datasets` → second tab, containing `## data_centers.csv` and `## data_center_chillers.csv` as side-by-side cards
- `# Altair demo` → third tab

You don't write any HTML or YAML to get the tabs — they fall out of the heading structure.

Default flow is **rows** (each `##` stacks vertically). To get side-by-side cards, see [Quarto dashboard layout](https://quarto.org/docs/dashboards/layout.html#orientation) — you can change orientation per page with `--- orientation: columns ---` or per `##` heading.

## How code chunks become cards

A Python chunk under a heading becomes a **card** in that section. Cell options control what kind of card:

```python
#| title: "data_centers.csv"     # gives the card a title bar
#| content: valuebox             # renders as a big KPI tile instead of a card
#| color: primary                # valuebox color
#| include: false                # hides the chunk — use for setup/imports
```

From `index.qmd`:

- The `imports` chunk at the top is `#| include: false` — runs but doesn't render. Use this for all `import` statements and data loading.
- The valuebox showing **"Current total capital cost"** uses `#| content: valuebox` with a `dict(value=...)` return.
- The two dataframe cards (`data_centers`, `data_center_chillers`) use `#| title:` and rely on `itables` for interactivity — just leaving the dataframe as the last expression in the chunk is enough.
- The Altair chart at the bottom is a plain chunk that returns an `alt.Chart(...).interactive()` — Quarto renders it as a card automatically.

The full reference of dashboard-specific cell options is in [Quarto dashboard data display](https://quarto.org/docs/dashboards/data-display.html).

## Adding a new section — recipe

Say you want to add a new tab showing chiller capacity by region.

1. **Add the page heading** at the bottom of `index.qmd`:

   ````markdown
   # Chillers by region

   ```{python}
   #| title: "Capacity by region"
   import altair as alt

   (
       alt.Chart(data_center_chillers)
          .mark_bar()
          .encode(x="Region:N", y="sum(Capacity (MW)):Q")
          .interactive()
   )
   ```
   ````

2. **Preview it** — `quarto preview` is already watching; save the file and the new tab appears.
3. **Want two charts side by side?** Wrap them in `##` headings under your `#` page, and add `orientation: columns` to the page or front matter.

## When to add a whole new `.qmd`

If you're building something that doesn't fit the dashboard (a long-form writeup, a methodology page), create a new `.qmd` at the repo root and add it to the navbar in `_quarto.yml`:

```yaml
website:
  navbar:
    left:
      - href: index.qmd
        text: Home
      - about.qmd
      - methodology.qmd      # ← new
```

The new page won't use `format: dashboard` — it'll inherit the site-wide HTML format from `_quarto.yml`.

## Bookmarks for authoring

- [Dashboard layout](https://quarto.org/docs/dashboards/layout.html) — rows, columns, tabsets, fill vs. flow
- [Dashboard data display](https://quarto.org/docs/dashboards/data-display.html) — value boxes, plots, tables, text
- [Python code cells](https://quarto.org/docs/computations/python.html) — chunk options reference
- [Migrating from R Markdown](https://quarto.org/docs/faq/rmarkdown.html) — for `.Rmd` muscle memory
