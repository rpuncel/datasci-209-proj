"""Unified, owner-linked "AI economy" explorer composite.

Combines the three choropleth maps (row 1) and the four owner charts (row 2)
into a *single* Altair spec. This is deliberate: Vega selections and shared
legends only work within one spec, so a single ``owner_clean`` selection can
link every view and one shared owner legend can drive them all. Every view also
draws from the same ``owner_scale()`` palette, so colors match across the page.

Render with::

    charts.interactive(ai_economy_explorer(df_us), id="ai-economy-explorer")

``capital_pipeline`` is a yearly aggregate with no owner dimension, so it sits in
the row for layout but does not respond to the owner selection (expected).
"""

import altair as alt
import pandas as pd

from charts import datacenters, electricity, money, water
from charts.owner_colors import owner_scale

# Uniform per-view sizing inside the concatenated rows. Tuned so three
# albersUsa maps (~1.6:1) sit side by side; retune against a real render.
MAP_WIDTH = 380
MAP_HEIGHT = 240
CHART_WIDTH = 300
CHART_HEIGHT = 260

# Grey applied to marks whose owner is not currently selected.
_DIM_COLOR = "#cbd5e1"


def ai_economy_explorer(df_us: pd.DataFrame) -> alt.VConcatChart:
    """Assemble the linked maps + charts figure keyed on a shared owner select.

    ``df_us`` is the US-only enriched centers frame (``dc.enriched_centers()``
    filtered to the United States) — it feeds the map overlays and the
    site-concentration bars.
    """
    owner_select = alt.selection_point(fields=["owner_clean"])
    scale = owner_scale()

    # Colour condition: selected owners keep their palette colour, everything
    # else greys out. ``legend=None`` — the owner legend is hosted separately so
    # only one appears (see ``test_explorer_has_single_owner_legend``).
    focus = alt.condition(
        owner_select,
        alt.Color("owner_clean:N", scale=scale, legend=None),
        alt.value(_DIM_COLOR),
    )
    dim = alt.condition(owner_select, alt.value(0.9), alt.value(0.25))

    def _sized(chart, title, *, w=MAP_WIDTH, h=MAP_HEIGHT):
        # Short titles: the baked-in map titles overflow at ~380px wide.
        return chart.properties(width=w, height=h, title=title)

    maps = alt.hconcat(
        _sized(
            money.capital_with_datacenters(df_us, color=focus, size_legend=True),
            "Capital by state",
        ),
        _sized(
            electricity.electricity_capacity_with_datacenters(
                df_us, color=focus, size_legend=False
            ),
            "Grid capacity",
        ),
        # Water hosts the single shared owner legend + a Power (MW) size legend.
        _sized(
            water.baseline_stress_with_datacenters(
                df_us, color=focus, size_legend=True
            ),
            "Water stress",
        ),
        spacing=18,
    )

    # The three owner-keyed charts are the click sources: ``add_params`` on each
    # unit ``Chart`` makes it fire the owner selection. The maps deliberately do
    # NOT get it — they respond via the focus/dim conditions (highlight-only).
    # (Making a map's point overlay a click source needs the layered-view + owner
    # selection wired explicitly; plain ``add_params`` on a ``LayerChart`` is
    # dropped by Altair's subchart param-merge, vega/altair#3891.)
    charts_row = alt.hconcat(
        # No owner dimension — static under the owner selection (expected).
        datacenters.capital_pipeline().properties(
            width=CHART_WIDTH, height=CHART_HEIGHT, title="Capital pipeline"
        ),
        datacenters.power_vs_capital_cost()
        .encode(color=focus, opacity=dim)
        .properties(width=CHART_WIDTH, height=CHART_HEIGHT, title="Power vs capital"),
        datacenters.owner_power()
        .encode(color=focus, opacity=dim)
        .add_params(owner_select)
        .properties(width=CHART_WIDTH, height=CHART_HEIGHT, title="Power by owner"),
        datacenters.site_concentration(df_us, lines=False)
        .encode(color=focus, opacity=dim)
        .properties(width=CHART_WIDTH, height=CHART_HEIGHT, title="Site concentration"),
        spacing=18,
    ).add_params(owner_select)

    return alt.vconcat(charts_row, maps, spacing=30)
