"""Water-stress choropleths (WRI Aqueduct 4.0) with data center overlays."""

import altair as alt
from altair.datasets import data
import pandas as pd

from wrangle import datacenters as wd
from wrangle import water as ww
from wrangle.datacenters import POWER


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
                legend=alt.Legend(title=legend_title, orient='right'),
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


def baseline_stress_with_datacenters(df: pd.DataFrame) -> alt.LayerChart:
    """Baseline stress choropleth with current AI data centers sized by power."""
    selection = alt.selection_point(fields=['owner_clean'], bind='legend')
    points = (
        alt.Chart(df.dropna(subset=["Latitude", "Longitude"]))
        .mark_circle(opacity=0.7, stroke="blue", strokeWidth=1)
        .encode(
            size=alt.Size(
                POWER,
                scale=alt.Scale(range=[20, 1000]),
                legend=alt.Legend(title="Power Capacity (MW)", orient='bottom'),
            ),
            longitude="Longitude:Q",
            latitude="Latitude:Q",
            tooltip=["Name:N", "Address:N", f"{POWER}:Q", "owner_clean:N"],
        )#.transform_filter(selection)
    )
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


def baseline_stress_owner_linked(df: pd.DataFrame) -> alt.HConcatChart:
    """Baseline stress map and site-concentration bars linked by owner selection.

    Clicking a bar or a data center point selects that owner and greys out
    everything else in both views. Needs an interactive renderer
    (charts.interactive), not the static SVG default.
    """
    from charts import datacenters  # deferred: charts/__init__ imports this module

    owners = sorted(
        set(wd.high_power_low_density()["owner_clean"].dropna())
        | set(df["owner_clean"].dropna())
    )
    owner_scale = alt.Scale(domain=owners, scheme="tableau20")
    owner_color = alt.Color("owner_clean:N", scale=owner_scale, title="Owner")
    brush = alt.selection_interval(encodings=['latitude', 'longitude'], fields=["Name"])
    brush_legend = alt.selection_point(fields=["owner_clean"], bind='legend')
    condition_legend = alt.when(brush_legend & brush).then(
        owner_color
    ).otherwise(alt.value("grey"))
    # the map's Owner legend covers both views
    bar_condition = alt.when(brush & brush_legend).then(
        owner_color.legend(None)
    ).otherwise(alt.value("grey"))

    company_bars = datacenters.site_concentration(df, lines=False).encode(color=bar_condition)

    points = (
        alt.Chart(df.dropna(subset=["Latitude", "Longitude"]))
        .mark_circle(opacity=0.7, strokeWidth=1)
        .encode(
            size=alt.Size(
                POWER,
                scale=alt.Scale(range=[20, 1000]),
                legend=alt.Legend(title="Power Capacity (MW)", orient='bottom'),
            ),
            color=condition_legend,
            longitude="Longitude:Q",
            latitude="Latitude:Q",
            tooltip=[
                "Name:N",
                "Address:N",
                f"{POWER}:Q",
                alt.Tooltip("owner_clean:N", title="Owner"),
            ],
        )
    ).add_params(brush_legend, brush)
    water_stress = (baseline_stress_choropleth() + points).properties(
        width=600,
        height=420,
        title="Baseline Water Stress by US State with Current AI Data Center Locations",
    )

    return (water_stress | company_bars)
