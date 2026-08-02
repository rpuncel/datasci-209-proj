"""Capital-cost choropleth (Epoch AI) with data center overlays.

Mirrors the water and electricity maps: a per-state choropleth joined to the
US states topojson on FIPS ``id``, with the shared data center point overlay
sized by per-site capital cost instead of power.
"""

import altair as alt
import pandas as pd

from charts import overlay
# Reuse water.py's cached, PR/USVI-filtered state features instead of the
# us_10m CDN topojson: it keeps albersUsa's auto-fit consistent with the other
# two maps, needs no runtime network fetch, and lets Altair's dataset
# consolidation embed the geometry once for all three maps in the explorer.
from charts.water import _states_map
from constants.states import STATE_FIPS, STATE_NAMES
from wrangle import datacenters as wd
from wrangle.datacenters import CAPEX

_ABBR_TO_NAME = {abbr: name for name, abbr in STATE_NAMES.items()}


def _capex_by_state():
    """Per-state capital totals keyed to topojson FIPS ``id`` (int).

    Every state is included so those with no AI data center read as 0 (lightest
    shade) rather than dropping out of the choropleth as unfilled white shapes.
    """
    summary = wd.state_summary().copy()  # 'state' is a two-letter abbreviation
    summary["stateName"] = summary["state"].map(_ABBR_TO_NAME)

    all_states = pd.DataFrame({"stateName": list(STATE_FIPS.keys())})
    all_states["id"] = all_states["stateName"].map(STATE_FIPS).astype(int)

    out = all_states.merge(
        summary[["stateName", "capex_b", "sites"]], on="stateName", how="left"
    )
    out["capex_b"] = out["capex_b"].fillna(0.0)
    out["sites"] = out["sites"].fillna(0).astype(int)
    return out


def capital_choropleth(*, legend: alt.Legend | None = None) -> alt.Chart:
    """State-level capital choropleth.

    ``legend`` lets a caller trade legend width for map width: at the default
    size the long title and full-length gradient are fine, but in
    ``charts.explorer`` this legend shares a narrow map's footprint with the
    site-capacity legend, and the pair together set the whole explorer's width.
    """
    capex = _capex_by_state()
    if legend is None:
        legend = alt.Legend(orient="bottom")
    return (
        alt.Chart(_states_map())
        .mark_geoshape(stroke="white", strokeWidth=0.5)
        .encode(
            color=alt.Color(
                "capex_b:Q",
                title="Data Center Capital (2025 USD B)",
                scale=alt.Scale(scheme="greens"),
                legend=legend,
            ),
            tooltip=[
                alt.Tooltip("stateName:N", title="State"),
                alt.Tooltip("capex_b:Q", title="Capital (USD B)", format=",.1f"),
                alt.Tooltip("sites:Q", title="Sites"),
            ],
        )
        .transform_lookup(
            lookup="id",
            from_=alt.LookupData(capex, "id", ["stateName", "capex_b", "sites"]),
        )
        .project(type="albersUsa")
        .properties(
            title="AI Data Center Capital by State (2025 USD Billions)",
        )
    )


def capital_with_datacenters(
    df: pd.DataFrame | None = None,
    controls: bool = False, *, color=None, size_legend: bool | alt.Legend = True
) -> alt.LayerChart:
    """Per-state capital choropleth with current AI data centers sized by capex.

    ``df`` defaults to the US-only enriched centers frame. ``controls=True``
    adds live jitter slider/checkbox (needs an interactive renderer); see
    ``jitter-lab.qmd``. ``color`` overrides the point color encoding (e.g. a
    shared owner-selection condition in the unified explorer); ``None`` keeps
    the standard owner palette. ``size_legend=False`` suppresses the size
    legend so a concatenated layout can host a single shared one.
    """
    if df is None:
        df = wd.us_centers()
    color_kwargs = {} if color is None else {"color": color}
    points = overlay.datacenter_points(
        df,
        size_field=CAPEX,
        size_title="Capital Cost (2025 USD B)",
        size_range=(30, 1200),
        size_legend=size_legend,
        **color_kwargs,
    )
    return (capital_choropleth() + points).resolve_scale(
        color="independent"
    ).properties(
        title="AI Data Center Capital by State with Site Locations",
    )
