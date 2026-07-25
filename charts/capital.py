"""Capital-cost choropleth (Epoch AI) with data center overlays.

Mirrors the water and electricity maps: a per-state choropleth joined to the
US states topojson on FIPS ``id``, with the shared data center point overlay
sized by per-site capital cost instead of power.
"""

import altair as alt
from altair.datasets import data
import pandas as pd

from charts import overlay
from constants.states import STATE_FIPS, STATE_NAMES
from wrangle import datacenters as wd
from wrangle import water as ww
from wrangle.datacenters import CAPEX
from wrangle.jitter import jitter_overlaps

_ABBR_TO_NAME = {abbr: name for name, abbr in STATE_NAMES.items()}


def _states_map():
    return alt.topo_feature(data.us_10m.url, feature="states")


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


def capital_choropleth() -> alt.Chart:
    capex = _capex_by_state()
    return (
        alt.Chart(_states_map())
        .mark_geoshape(stroke="white", strokeWidth=0.5)
        .encode(
            color=alt.Color(
                "capex_b:Q",
                title="Data Center Capital (2025 USD B)",
                scale=alt.Scale(scheme="greens"),
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
            width=800,
            height=500,
            title="AI Data Center Capital by State (2025 USD Billions)",
        )
    )


def capital_with_datacenters() -> alt.LayerChart:
    """Per-state capital choropleth with current AI data centers sized by capex."""
    df = jitter_overlaps(
        ww.us_centers_geocoded().dropna(subset=["Latitude", "Longitude"]),
        size=CAPEX,
        spread=overlay.JITTER_SPREAD,
    )
    points = overlay.datacenter_points(
        df,
        size_field=CAPEX,
        size_title="Capital Cost (2025 USD B)",
        size_range=(30, 1200),
        tooltip=[
            "Name:N",
            "Address:N",
            alt.Tooltip(f"{CAPEX}:Q", title="Capital (USD B)", format=",.1f"),
            alt.Tooltip("owner_clean:N", title="Owner"),
        ],
    )
    return (capital_choropleth() + points).properties(
        title="AI Data Center Capital by State with Site Locations",
    )
