"""electricity choropleths (EIA 2024) with data center overlays."""

import altair as alt
from altair.datasets import data
import pandas as pd

#from wrangle import electricity as we
from wrangle.datacenters import POWER, us_centers_geocoded
from constants.states import STATE_FIPS

def us_electricity_capacity():
    eia_df = pd.read_csv("datasets/eia_state_total_capability_2024.csv")

    # ensure numeric
    eia_df["capability"] = pd.to_numeric(eia_df["capability"], errors="coerce")

    # map state name → FIPS (as STRING, matching topojson)
    eia_df["id"] = eia_df["stateDescription"].map(STATE_FIPS)
    eia_df = eia_df.dropna(subset=["id"]) #drop unmapped rows
    eia_df["id"] = eia_df["id"].astype(int) # convert to int

    # IMPORTANT: drop rows that didn't map (safety)
    eia_df = eia_df.dropna(subset=["id"])

    # aggregate to state level
    eia_df = (
        eia_df.groupby(["id", "stateDescription"], as_index=False)["capability"]
        .sum()
    )
    return eia_df


def _states_map():
    return alt.topo_feature(data.us_10m.url, feature="states")

def electricity_capacity_choropleth():
    eia_df = us_electricity_capacity().copy()


    return (
        alt.Chart(_states_map())
        .mark_geoshape(stroke="white")
        .encode(
            color=alt.Color(
                "capability:Q",
                title="Installed Capacity (MW)",
                scale=alt.Scale(scheme="oranges"),
            ),
            tooltip=[
                alt.Tooltip("stateDescription:N", title="State"),
                alt.Tooltip("capability:Q", title="Capacity (MW)", format=",.0f"),
            ],
        )
        .transform_lookup(
            lookup="id",
            from_=alt.LookupData(
                eia_df,
                "id",
                ["stateDescription", "capability"],
            ),
        )
        .project(type="albersUsa")
        .properties(
            width=800,
            height=500,
            title="Installed Electricity Capacity by State (2024)",
        )
    )

def electricity_capacity_with_datacenters() -> alt.LayerChart:
    """Installed generation capacity with AI data centers."""
    eia_df = us_electricity_capacity().copy()

    points = (
        alt.Chart(
            us_centers_geocoded().dropna(subset=["Latitude", "Longitude"])
        )
        .mark_circle(
            color="black",
            opacity=0.7,
            stroke="white",
            strokeWidth=1,
        )
        .encode(
            longitude="Longitude:Q",
            latitude="Latitude:Q",
            size=alt.Size(
                POWER,
                scale=alt.Scale(range=[20, 1000]),
                legend=alt.Legend(title="Power Capacity (MW)"),
            ),
            tooltip=[
                "Name:N",
                "Address:N",
                alt.Tooltip(f"{POWER}:Q", title="Data Center MW"),
            ],
        )
    )

    return (
        electricity_capacity_choropleth() + points
    ).properties(
        title="2024 Installed Electricity Capacity and AI Data Centers"
    )
