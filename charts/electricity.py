"""electricity choropleths (EIA 2024) with data center overlays."""

from wrangle.datacenters import enriched_centers
import altair as alt
import pandas as pd

#from wrangle import electricity as we
from wrangle.datacenters import POWER
from constants.states import STATE_FIPS
# Reuse water.py's filtered map (drops Puerto Rico/US Virgin Islands, which
# have no matching EIA rows and skew albersUsa's auto-fit) so this map
# centers the same way the water map's width=1080/height=540 tuning does.
from charts.water import _states_map

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


def electricity_capacity_choropleth():
    eia_df = us_electricity_capacity().copy()


    return (
        alt.Chart(_states_map())
        .mark_geoshape(stroke="white")
        .encode(
            color=alt.Color(
                "capability:Q",
                title="Installed Grid Capacity (MW)",
                scale=alt.Scale(range=['#FFD700', '#4A4A4A']),
                # Positioned like water.py's map legends: orient="none" +
                # explicit legendX/legendY puts this and the size legend below
                # side by side on one row, instead of bottom's auto-stack.
                legend=alt.Legend(orient="none", legendX=0, legendY=555, direction="horizontal", gradientLength=250),
            ),
            tooltip=[
                alt.Tooltip("stateDescription:N", title="State"),
                alt.Tooltip("capability:Q", title="Grid Capacity (MW)", format=",.0f"),
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
            width=1080,
            height=540,
            title="Installed Electricity Capacity by State (2024)",
        )
    )

def electricity_capacity_with_datacenters() -> alt.LayerChart:
    """Installed generation capacity with AI data centers."""
    eia_df = us_electricity_capacity().copy()

    # Non-US sites (China, Malaysia, Indonesia, Portugal, UAE in the current
    # data) have longitudes far outside the continental range and don't
    # belong on a US-only albersUsa map.
    us_centers = enriched_centers()
    us_centers = us_centers[us_centers["Country"] == "United States"]
    points = (
        alt.Chart(
            us_centers.dropna(subset=["Latitude", "Longitude"])
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
                legend=alt.Legend(
                    title="Data Center Power Use (MW)",
                    orient="none",
                    legendX=420,
                    legendY=555,
                    direction="horizontal",
                ),
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
        # Plain-string titles default to a centered anchor on a standalone
        # view; anchor="start" keeps this flush left. (A negative dx here to
        # counter the padding below looks like the fix, but Vega's autosize
        # reacts to dx by growing the canvas ~2x the offset, pushing the
        # title even further right — the CSS rule in styles.css cancels the
        # padding for the title instead, without touching layout/autosize.)
        title=alt.Title(
            "2024 Installed Electrical Grid Capacity and AI Data Centers Power Use",
            anchor="start",
        ),
        # The water map's map_chart sits inside a vconcat with a title dx
        # hack and wider legends, both of which push its rendered content
        # right by ~158px more than this chart gets on its own. Padding is
        # the deterministic way to reproduce that offset here (verified by
        # comparing rendered pixel positions of both maps' west coasts)
        # instead of chasing the same fragile auto-fit/legend-overflow
        # interaction that produced it for water.
        padding={"left": 158, "top": 5, "right": 5, "bottom": 5},
    )
