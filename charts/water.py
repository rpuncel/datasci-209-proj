"""Water-stress choropleths (WRI Aqueduct 4.0) with data center overlays."""

import altair as alt
from altair.datasets import data

from charts import overlay
from wrangle import water as ww
from wrangle.datacenters import POWER
from wrangle.jitter import jitter_overlaps


def _states_map():
    return alt.topo_feature(data.us_10m.url, feature="states")


def water_stress_geo_map() -> alt.Chart:
    """Province-level water stress drawn from the Aqueduct geodatabase polygons."""
    return alt.Chart(ww.aqueduct_geo(), title="Water Stress Map").mark_geoshape().encode(
        alt.Color("bws_label:O")
    ).project(type="albersUsa", reflectY=True).properties(width=600)


def _stress_choropleth(stress, legend_title: str, chart_title: str, **mark_kwargs) -> alt.Chart:
    return (
        alt.Chart(_states_map())
        .mark_geoshape(**mark_kwargs)
        .encode(
            color=alt.Color(
                "score:Q",
                scale=alt.Scale(scheme="reds", domain=[0, 5]),
                legend=alt.Legend(title=legend_title),
            ),
            tooltip=[
                alt.Tooltip("name_1:N", title="State"),
                alt.Tooltip("score:Q", title="Score", format=".2f"),
                alt.Tooltip("label:N", title="Category"),
            ],
        )
        .transform_lookup(
            lookup="id",
            from_=alt.LookupData(stress, "id", ["name_1", "score", "label"]),
        )
        .project(type="albersUsa")
        .properties(width=800, height=500, title=chart_title)
    )


def baseline_stress_choropleth() -> alt.Chart:
    return _stress_choropleth(
        ww.us_water_stress(),
        legend_title="Baseline Water Stress",
        chart_title="Baseline Water Stress by US State (Aqueduct 4.0)",
    )


def future_stress_choropleth() -> alt.Chart:
    return _stress_choropleth(
        ww.future_us_water_stress(),
        legend_title="Future Water Stress",
        chart_title="Future Water Stress by US State (Aqueduct 4.0)",
        stroke="white",
        strokeWidth=0.5,
    )


def baseline_stress_with_datacenters(controls: bool = False) -> alt.LayerChart:
    """Baseline stress choropleth with current AI data centers sized by power.

    ``controls=True`` adds live jitter slider/checkbox (needs an interactive
    renderer); see ``jitter-lab.qmd``.
    """
    df = jitter_overlaps(
        ww.us_centers_geocoded().dropna(subset=["Latitude", "Longitude"]),
        size=POWER,
        spread=overlay.JITTER_SPREAD,
        cluster_dist=overlay.CLUSTER_DIST,
    )
    points = overlay.datacenter_points(df, jitter_controls=controls)
    return (baseline_stress_choropleth() + points).properties(
        width=800,
        height=500,
        title="Baseline Water Stress by US State with Current AI Data Center Locations",
    )


def future_stress_with_datacenters() -> alt.LayerChart:
    """Future stress choropleth with proposed data centers (not AI-specific)."""
    points = (
        alt.Chart(ww.future_data_centers().dropna(subset=["lat", "long"]))
        .mark_circle(color="black", opacity=0.7, stroke="blue", strokeWidth=1)
        .encode(
            longitude="long:Q",
            latitude="lat:Q",
            tooltip=["Name:N", "Address:N", "mw:Q"],
        )
    )
    return (future_stress_choropleth() + points).properties(
        width=800,
        height=500,
        title="Future Water Stress by US State with Proposed Data Center Locations",
    )


def stress_comparison() -> alt.HConcatChart:
    """Current and future stress maps side by side."""
    return baseline_stress_with_datacenters() | future_stress_with_datacenters()



# The owner-linked, cross-filtered flagship map lives in charts.flagship_map.
