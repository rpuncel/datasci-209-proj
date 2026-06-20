# Context: Visualizing the AI Economy

## Purpose

This dashboard communicates trends in the AI economy to a general-data-literate audience. The primary data source is Epoch AI's frontier data centers dataset (CC BY 4.0). Additional datasets may be added over the project lifetime.

## Glossary

| Term | Definition |
|------|-----------|
| **frontier model** | A state-of-the-art AI model pushing the boundary of capability at time of release |
| **frontier data center** | A large-scale compute facility built or announced to train frontier-class AI models |
| **training compute** | The total floating-point operations (FLOPs) used to train a model |
| **QMD file** | A Quarto Markdown source file (`.qmd`); the authoring unit for this project |
| **value box** | A Quarto dashboard card showing a single KPI metric with an icon and label |
| **card** | A panel in the Quarto dashboard layout; contains one chart, table, or value box |
| **page** | A top-level tab in the Quarto dashboard, defined by a `#` heading in `.qmd` |

## Data sources

- **Epoch AI frontier data centers** — primary dataset; downloaded at render time into `data/`. Covers announced/built frontier data centers, their operators, locations, planned compute capacity, and timeline.

## Architecture decisions

No ADRs yet. As decisions get resolved, record them in `docs/adr/` using the format `NNNN-short-title.md`.

## What this project is NOT

- Not a research paper — clarity and accessibility over statistical rigor
- Not a real-time dashboard — data is static, fetched at Quarto render time
- Not a production app — deployed on Posit Connect Cloud for course use
