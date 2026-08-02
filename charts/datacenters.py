"""Reusable Altair charts for the Epoch AI data center analysis.

Each function is zero-arg and returns the chart object, so any .qmd cell can
show one with e.g. ``charts.datacenters.owner_power()``. Callers that need a
different size (dashboards vs. slides) can chain ``.properties(...)``.
"""

import altair as alt
import pandas as pd

from charts.owner_colors import owner_color
from wrangle import datacenters as dc
from wrangle.datacenters import CAPEX, POWER, H100


def cost_vs_energy() -> alt.Chart:
    centers = dc.enriched_centers()
    return alt.Chart(centers, title="Data Center Cost vs Energy Use").mark_circle(
        opacity=0.78, stroke="white", strokeWidth=1
    ).encode(
        x=alt.X(f"{CAPEX}:Q", title=CAPEX),
        y=alt.Y(f"{POWER}:Q", title=POWER),
        color=owner_color(legend=None),
        tooltip=[
            alt.Tooltip(f"{CAPEX}:Q"),
            alt.Tooltip(f"{POWER}:Q"),
            alt.Tooltip("owner_clean:N", title="Owner"),
        ],
    ).properties(
        width=800,
        height=400,
    )

def compute_vs_power() -> alt.Chart:
    centers = dc.enriched_centers()
    return alt.Chart(centers, title="Data Center Compute Power vs Energy Use").mark_circle(
        opacity=0.78, stroke="white", strokeWidth=1
    ).encode(
        x=alt.X(f"{H100}:Q", title=H100),
        y=alt.Y(f"{POWER}:Q", title=POWER),
        color=owner_color(legend=None),
        tooltip=[
            alt.Tooltip(f"{CAPEX}:Q"),
            alt.Tooltip(f"{POWER}:Q"),
            alt.Tooltip("owner_clean:N", title="Owner"),
        ],
    ).properties(
        width=800,
        height=400,
    )



def state_power() -> alt.Chart:
    centers = dc.enriched_centers()
    # This early exploratory chart keeps its original, simpler state extraction:
    # the two-letter abbreviation preceding a ZIP code in the address.
    zip_state = centers["Address"].str.extract(r",\s*([A-Z]{2})\s*\d{5}")[0]
    centers = centers.assign(state=zip_state)
    return alt.Chart(
        centers[centers["state"].notna()]
    ).mark_bar(stroke="white", strokeWidth=1).encode(
        x=alt.X("state:N", title="State"),
        y=alt.Y(f"sum({POWER}):Q", title="Total Power Use (MW)"),
        order=alt.Order("Name:N"),
        tooltip=["state:N", "Name:N", f"sum({POWER}):Q"],
    ).properties(
        title="Data Center Energy Use by State",
        width=800,
        height=400,
    )


def owner_power() -> alt.Chart:
    return alt.Chart(dc.owner_summary().head(10)).mark_bar().encode(
        y=alt.Y("owner_clean:N", sort="-x", title=None),
        x=alt.X("power_mw:Q", title="Estimated current power (MW)"),
        color=owner_color(legend=None),
        tooltip=[
            alt.Tooltip("owner_clean:N", title="Owner"),
            alt.Tooltip("power_mw:Q", title="Power (MW)", format=",.0f"),
            alt.Tooltip("capex_b:Q", title="Capital cost ($B)", format=",.1f"),
            alt.Tooltip("sites:Q", title="Sites", format=","),
            alt.Tooltip("power_share:Q", title="Power share", format=".1%"),
        ],
    ).properties(
        title=alt.Title(
            "Current AI data center power is concentrated by owner",
            subtitle=f"The top four owner groups account for {dc.stats().top4_owner_share:.1%} of estimated current power.",
            anchor="start",
        ),
        height=360,
    )


def site_concentration(*params, df: pd.DataFrame | None = None, lines=True, color: alt.Color | None) -> alt.LayerChart:
    if color is None:
        color = owner_color()
    site_rank = (dc.us_centers() if df is None else df).sort_values("rank")
    site_bars = alt.Chart(site_rank.head(20), name="site_bars").mark_bar().encode(
        x=alt.X("rank:O", title="Site rank by current power"),
        y=alt.Y(f"{POWER}:Q", title="Current power (MW)"),
        color=color,
        tooltip=[
            alt.Tooltip("rank:O", title="Rank"),
            alt.Tooltip("Name:N", title="Data center"),
            alt.Tooltip("owner_clean:N", title="Owner"),
            alt.Tooltip(f"{POWER}:Q", title="Power (MW)", format=",.0f"),
            alt.Tooltip("Country:N", title="Country"),
        ],
    ).add_params(*params)
    if lines:
        site_line = alt.Chart(site_rank.head(20)).mark_line(
            point=True, strokeWidth=3
        ).encode(
            x=alt.X("rank:O"),
            y=alt.Y("cumulative_power_share:Q", title="Cumulative share", axis=alt.Axis(format="%")),
            tooltip=[
                alt.Tooltip("Name:N", title="Data center"),
                alt.Tooltip("cumulative_power_share:Q", title="Cumulative power share", format=".1%"),
            ],
        )
        return (site_bars + site_line).resolve_scale(y="independent").properties(
            title=alt.Title(
                "A few large sites account for much of the current footprint",
                subtitle=f"The top 10 sites represent {dc.stats().top10_power_share:.1%} of estimated current power.",
                anchor="start",
            ),
            height=390,
        )
    else:
        return  site_bars.properties(
            title=alt.Title(
                "A few large sites account for much of the current footprint",
                subtitle=f"The top 10 sites represent {dc.stats().top10_power_share:.1%} of estimated current power.",
                anchor="start",
            ),
            height=390,
        )


def power_vs_capital_cost() -> alt.Chart:
    return alt.Chart(dc.owner_summary().head(10)).mark_circle(
        opacity=0.78, stroke="white", strokeWidth=1
    ).encode(
        x=alt.X("power_mw:Q", title="Estimated current power (MW)"),
        y=alt.Y("capex_b:Q", title="Estimated current capital cost (2025 USD billions)"),
        # Manually stacked (rather than orient="bottom", which crowded the two
        # legends together): Owner wraps to 2 rows, so H100's legendY needs
        # enough clearance below it to read as a separate line, not orient
        # auto-stacking's tighter default gap.
        size=alt.Size(
            "h100_eq:Q",
            title="H100 equivalents",
            scale=alt.Scale(range=[80, 1500]),
            # Explicit values instead of Vega-Lite's auto ticks, which some
            # renderers expand to more entries than this legend has room for.
            legend=alt.Legend(
                values=[300000, 900000, 1500000],
            ),
        ),
        color=owner_color(),
        tooltip=[
            alt.Tooltip("owner_clean:N", title="Owner"),
            alt.Tooltip("power_mw:Q", title="Power (MW)", format=",.0f"),
            alt.Tooltip("capex_b:Q", title="Capital cost ($B)", format=",.1f"),
            alt.Tooltip("h100_eq:Q", title="H100 equivalents", format=",.0f"),
        ],
    ).properties(
        title=alt.Title(
            "The amount of power capacity a data center correlates to the amount of investment",
            subtitle="Owner groups with the most power also carry the largest estimated capital footprint.",
            anchor="start",
        ),
        height=380,
    )


def timeline_with_milestones() -> alt.LayerChart:
    growth_power = alt.Chart(dc.yearly()).mark_line(point=True, strokeWidth=3).encode(
        x=alt.X("date:T", title="Year-end", axis=alt.Axis(format="%Y")),
        y=alt.Y("power_mw:Q", title="Estimated portfolio power (MW)"),
        color=alt.Color("record_type:N", title="Record type"),
        tooltip=[
            alt.Tooltip("date:T", title="Year-end", format="%Y-%m-%d"),
            alt.Tooltip("power_mw:Q", title="Power (MW)", format=",.0f"),
            alt.Tooltip("data_centers:Q", title="Data centers", format=","),
            alt.Tooltip("record_type:N", title="Record type"),
        ],
    )
    event_rules = alt.Chart(dc.events()).mark_rule(color="#d9822b", strokeDash=[5, 5]).encode(
        x="date:T",
        tooltip=[
            alt.Tooltip("event:N", title="Milestone"),
            alt.Tooltip("date:T", title="Date", format="%Y-%m-%d"),
        ],
    )
    event_labels = alt.Chart(dc.events()).mark_text(
        align="left",
        baseline="middle",
        dx=5,
        fontSize=11,
        lineBreak="\n",
        color="#8a4f13",
    ).encode(
        x="date:T",
        y=alt.Y("label_y:Q", title=None),
        text="label:N",
    )
    return (growth_power + event_rules + event_labels).properties(
        title=alt.Title(
            "The buildout curve bends upward after the generative-AI inflection",
            subtitle="Milestone labels use exact event dates and align with the vertical rules.",
            anchor="start",
        ),
        height=420,
    )


def annual_additions() -> alt.Chart:
    yearly = dc.yearly()
    return alt.Chart(yearly[yearly["year"] >= 2021]).mark_bar().encode(
        x=alt.X("year:O", title="Year"),
        y=alt.Y("added_power_mw:Q", title="Added power versus prior year (MW)"),
        color=alt.Color("record_type:N", title="Record type"),
        tooltip=[
            alt.Tooltip("year:O", title="Year"),
            alt.Tooltip("added_power_mw:Q", title="Added power (MW)", format=",.0f"),
            alt.Tooltip("power_mw:Q", title="Year-end total power (MW)", format=",.0f"),
            alt.Tooltip("record_type:N", title="Record type"),
        ],
    ).properties(
        title=alt.Title(
            "The acceleration is lumpy, not smooth",
            subtitle="Large additions in the timeline are concentrated in a few years.",
            anchor="start",
        ),
        height=360,
    )


def capital_pipeline() -> alt.Chart:
    return alt.Chart(dc.yearly()).mark_area(line=True, opacity=0.35).encode(
        x=alt.X("date:T", title="Year-end", axis=alt.Axis(format="%Y")),
        y=alt.Y("capex_b:Q", title="Estimated capital cost (2025 USD billions)"),
        tooltip=[
            alt.Tooltip("date:T", title="Year-end", format="%Y-%m-%d"),
            alt.Tooltip("capex_b:Q", title="Capital cost ($B)", format=",.1f"),
            alt.Tooltip("power_mw:Q", title="Power (MW)", format=",.0f"),
        ],
    ).properties(
        title=alt.Title(
            "By 2030, over a trillion dollars will be spent to build data centers",
            anchor="start",
        ),
    )


def power_vs_compute_density() -> alt.LayerChart:
    stats = dc.stats()
    owner_select = alt.selection_point(fields=["owner_clean"], bind="legend")
    median_rule = pd.DataFrame({"median_density": [stats.median_density]})

    scatter = alt.Chart(dc.valid_density()).mark_circle(
        opacity=0.76, stroke="white", strokeWidth=1
    ).encode(
        x=alt.X(f"{POWER}:Q", title="Current power (MW)"),
        y=alt.Y("h100_per_mw:Q", title="H100 equivalents per MW"),
        size=alt.Size(f"{CAPEX}:Q", title="Capital cost ($B)", scale=alt.Scale(range=[45, 1100])),
        color=owner_color(),
        opacity=alt.condition(owner_select, alt.value(0.82), alt.value(0.16)),
        tooltip=[
            alt.Tooltip("Name:N", title="Data center"),
            alt.Tooltip("owner_clean:N", title="Owner"),
            alt.Tooltip(f"{POWER}:Q", title="Power (MW)", format=",.0f"),
            alt.Tooltip("h100_per_mw:Q", title="H100 equivalents per MW", format=",.0f"),
            alt.Tooltip(f"{CAPEX}:Q", title="Capital cost ($B)", format=",.1f"),
        ],
    ).add_params(owner_select)

    rule = alt.Chart(median_rule).mark_rule(color="#d9822b", strokeDash=[5, 5]).encode(
        y="median_density:Q",
        tooltip=[alt.Tooltip("median_density:Q", title="Median density", format=",.0f")],
    )

    return (scatter + rule).properties(
        title=alt.Title(
            "Power does not translate into compute capacity evenly",
            subtitle=f"Dashed line marks the median: {stats.median_density:,.0f} H100 equivalents per MW.",
            anchor="start",
        ),
        height=420,
    )


def higher_power_lower_density_sites() -> alt.Chart:
    return alt.Chart(dc.high_power_low_density()).mark_bar().encode(
        y=alt.Y("Name:N", sort="x", title=None),
        x=alt.X("h100_per_mw:Q", title="H100 equivalents per MW"),
        color=owner_color(),
        tooltip=[
            alt.Tooltip("Name:N", title="Data center"),
            alt.Tooltip("owner_clean:N", title="Owner"),
            alt.Tooltip(f"{POWER}:Q", title="Power (MW)", format=",.0f"),
            alt.Tooltip("h100_per_mw:Q", title="H100 equivalents per MW", format=",.0f"),
        ],
    ).properties(
        title=alt.Title(
            "Some high-power sites produce fewer H100-equivalents per MW",
            subtitle=f"Filtered to sites at or above the median power level of {dc.stats().median_power:,.0f} MW and below median compute density.",
            anchor="start",
        ),
        height=390,
    )


def continental_comparison() -> alt.Chart:
    return alt.Chart(dc.continent_summary()).mark_bar().encode(
        y=alt.Y("continent:N", sort="-x", title=None),
        x=alt.X("power_mw:Q", title="Estimated current power (MW)"),
        color=alt.Color("continent:N", legend=None, scale=alt.Scale(scheme="set2")),
        tooltip=[
            alt.Tooltip("continent:N", title="Continent"),
            alt.Tooltip("power_mw:Q", title="Power (MW)", format=",.0f"),
            alt.Tooltip("capex_b:Q", title="Capital cost ($B)", format=",.1f"),
            alt.Tooltip("sites:Q", title="Sites", format=","),
            alt.Tooltip("power_share:Q", title="Share of power", format=".1%"),
        ],
    ).properties(
        title=alt.Title(
            "North America dominates estimated current AI data center power",
            subtitle="The geographic footprint is heavily weighted toward U.S. sites.",
            anchor="start",
        ),
        height=330,
    )


def us_state_concentration() -> alt.Chart:
    return alt.Chart(dc.state_summary().head(15)).mark_bar().encode(
        y=alt.Y("state:N", sort="-x", title=None),
        x=alt.X("power_mw:Q", title="Estimated current power (MW)"),
        color=alt.Color("power_mw:Q", title="Power (MW)", scale=alt.Scale(scheme="viridis")),
        tooltip=[
            alt.Tooltip("state:N", title="State"),
            alt.Tooltip("sites:Q", title="Sites", format=","),
            alt.Tooltip("power_mw:Q", title="Power (MW)", format=",.0f"),
            alt.Tooltip("capex_b:Q", title="Capital cost ($B)", format=",.1f"),
            alt.Tooltip("power_share:Q", title="Share of U.S. power", format=".1%"),
        ],
    ).properties(
        title=alt.Title(
            "Within the U.S., power is concentrated in a handful of states",
            subtitle=f"The top five known states account for {dc.stats().top_state_power_share:.1%} of U.S. estimated current power with known state labels.",
            anchor="start",
        ),
        height=440,
    )
