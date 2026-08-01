"""Water-stress choropleths (WRI Aqueduct 4.0) with data center overlays."""

from functools import lru_cache
from pathlib import Path

import altair as alt
import geopandas as gpd
import pandas as pd
import requests
from altair.datasets import data
import pandas as pd

from constants import STATE_FIPS
from charts.owner_colors import owner_scale
from wrangle import datacenters as wd
from wrangle import water as ww
from wrangle.datacenters import POWER


@lru_cache(maxsize=None)
def _states_map():
    """The original Vega U.S. map converted to embedded state features."""
    cache = Path(__file__).parents[1] / "data" / "external" / "us-10m.json"
    if not cache.exists():
        response = requests.get(data.us_10m.url, timeout=30)
        response.raise_for_status()
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(response.text)
    states = gpd.read_file(cache, layer="states")
    states["id"] = states["id"].astype(int)
    # The source topology also includes Puerto Rico and the US Virgin
    # Islands, which have no matching Aqueduct data and sit far enough
    # southeast that they skew albersUsa's automatic fit/centering.
    valid_ids = {int(fips) for fips in STATE_FIPS.values()}
    return states[states["id"].isin(valid_ids)].reset_index(drop=True)


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


def water_stress_explorer() -> alt.VConcatChart:
    """A timeline-led water-stress story with linked owners and state change."""
    comparison = ww.water_stress_wide()

    def selected_projection(column: str) -> str:
        return (
            f"water_step == 1 ? datum.{column}_2030_bau : "
            f"water_step == 2 ? datum.{column}_2050_bau : "
            f"datum.{column}_2080_bau"
        )

    projection_fields = ["name_1", "baseline_score", "baseline_label"]
    for year in ww.FUTURE_YEARS:
        for scenario_code in ww.SCENARIOS:
            suffix = f"{year}_{scenario_code}"
            projection_fields.extend(
                [
                    f"future_score_{suffix}",
                    f"future_label_{suffix}",
                    f"delta_{suffix}",
                ]
            )

    period = alt.param(
        name="water_step",
        value=0,
        bind=alt.binding_range(min=0, max=3, step=1, name="Explore Water Stress over Time: "),
    )
    show_future = alt.param( # add parameter for future datasite toggle switch 
        name="show_future_sites",
        value=False, #default to off 
        bind=alt.binding_checkbox(name="Show proposed data centers: "),
    )
    state_hover = alt.selection_point(
        name="water_state_hover",
        fields=["id"],
        on="pointerover",
        clear="pointerout",
        empty=False,
    )
    state_pin = alt.selection_point(
        name="water_state_pin",
        fields=["id"],
        on="click",
        clear="dblclick",
        empty=False,
    )
    owner_select = alt.selection_point(
        name="water_owner_select",
        fields=["operator"],
        on="click",
        clear="dblclick",
        empty=True,
    )
    # Geographic rubber-band brush (ported from baseline_stress_owner_linked).
    # Dragging a box on the map restricts owner_bars to the sites inside it, so
    # the "who controls the most capacity" ranking recomputes for that region.
    map_brush = alt.selection_interval(
        name="water_map_brush",
        encodings=["longitude", "latitude"],
        empty=True,
    )

    period_label = (
        "water_step == 0 ? 'Baseline' : "
        "(water_step == 1 ? '2030' : water_step == 2 ? '2050' : '2080')"
    )
    state_data = (
        alt.Chart(_states_map())
        .transform_lookup(
            lookup="id",
            from_=alt.LookupData(comparison, "id", projection_fields),
        )
        .transform_calculate(
            display_score=(
                "water_step == 0 ? datum.baseline_score : "
                f"{selected_projection('future_score')}"
            ),
            display_label=(
                "water_step == 0 ? datum.baseline_label : "
                f"{selected_projection('future_label')}"
            ),
            selected_period=f"{period_label}",
            selected_scenario=(
                "water_step == 0 ? 'Observed baseline' : 'Business as usual'"
            ),
            selected_forecast=(
                "water_step == 0 ? null : "
                f"{selected_projection('future_score')}"
            ),
            selected_delta=(
                "water_step == 0 ? null : "
                f"{selected_projection('delta')}"
            ),
        )
    )
    state_tooltip = [
        alt.Tooltip("name_1:N", title="State"),
        alt.Tooltip("selected_period:N", title="Period"),
        alt.Tooltip("selected_scenario:N", title="Pathway"),
        alt.Tooltip("display_score:Q", title="Water stress", format=".2f"),
        alt.Tooltip("display_label:N", title="Category"),
        alt.Tooltip("baseline_score:Q", title="Baseline", format=".2f"),
        alt.Tooltip("selected_forecast:Q", title="Forecast", format=".2f"),
        alt.Tooltip("selected_delta:Q", title="Change", format="+.2f"),
    ]
    outline = {
        "stroke": alt.condition(
            state_pin | state_hover, alt.value("#4a1d1f"), alt.value("#ffffff")
        ),
        "strokeWidth": alt.condition(
            state_pin | state_hover, alt.value(1.7), alt.value(0.65)
        ),
    }
    no_data = state_data.mark_geoshape(
        fill="#f1f5f9", stroke="#ffffff", strokeWidth=0.7
    )
    stress = (
        state_data.mark_geoshape()
        .encode(
            color=alt.Color(
                "display_score:Q",
                scale=alt.Scale(domain=[0, 5], scheme="reds"),
                legend=alt.Legend(
                    title="Water stress score (0 = low, 5 = extremely high)",
                    titleLimit=380,
                    orient="none",
                    legendX=0,
                    legendY=555,
                    direction="horizontal",
                    gradientLength=250,
                ),
            ),
            tooltip=state_tooltip,
            **outline,
        )
        # Bind the state selections to the geoshape marks themselves. Added at
        # the vconcat level they never fire (no marks to listen to); on this
        # unit view, hover/click on a state drives the map outline AND the
        # linked emphasis on the delta chart below.
        .add_params(state_hover, state_pin)
    )

    sites = ww.comparison_sites()
    owner_domain = sorted(sites["operator"].dropna().unique().tolist())
    shared_owner_scale = owner_scale(owner_domain)
    owner_focus_color = alt.condition(
        owner_select,
        alt.Color("operator:N", scale=shared_owner_scale, legend=None),
        alt.value("#cbd5e1"),
    )
    # When the timeline is past Baseline: show Future sites only if the
    # checkbox is on, otherwise fall back to showing the Baseline sites
    # instead of leaving the map empty.
    site_filter = (
        "datum.site_period == 'Baseline' || "
        "(datum.site_period == 'Future' && show_future_sites)"
    )
    site_tooltip = [
        alt.Tooltip("site_name:N", title="Site"),
        alt.Tooltip("site_type:N", title="Type"),
        alt.Tooltip("operator:N", title="Owner / operator"),
        alt.Tooltip("address:N", title="Address"),
        alt.Tooltip("capacity_mw:Q", title="Data Center Capacity (MW)", format=",.0f"),
    ]
    site_points = (
        alt.Chart(sites)
        .transform_filter(site_filter)
        .transform_filter("datum.capacity_mw > 0")
        .mark_point(filled=True, stroke="#ffffff", strokeWidth=0.9)
        .encode(
            longitude="longitude:Q",
            latitude="latitude:Q",
            size=alt.Size(
                "capacity_mw:Q",
                # capacity_mw is heavily right-skewed (73% of sites are under
                # 500 MW, out of a 0-7000 MW range) so a linear scale crowds
                # most points into the smallest sliver of the size range.
                # sqrt spreads out that common low end at the cost of some
                # separation among the rare, very large outliers.
                scale=alt.Scale(type="sqrt", domain=[0, 3000], range=[30, 650], clamp=True),
                legend=alt.Legend(
                    title="Site capacity (MW)",
                    orient="none",
                    legendX=320,
                    legendY=555,
                    direction="horizontal",
                    values=[100, 600, 1800, 3000],
                ),
            ),
            color=owner_focus_color,
            shape=alt.Shape(
                "site_type:N",
                scale=alt.Scale(
                    domain=["Current AI site", "Proposed project"],
                    range=["circle", "triangle-up"],
                ),
                legend=alt.Legend(
                    title="Site layer",
                    orient="none",
                    legendX=611,
                    legendY=555,
                    direction="horizontal",
                    # Default legend symbols render tiny (~10px) next to the
                    # much larger size-encoded circles above; bump them up
                    # so the shapes are actually legible.
                    symbolSize=350,
                ),
            ),
            opacity=alt.condition(
                owner_select & map_brush, alt.value(0.98), alt.value(0.28)
            ),
            tooltip=site_tooltip,
        )
        .add_params(map_brush) # add show_future param for toggle
    )
    map_chart = (
        alt.layer(no_data, stress, site_points)
        .project(type="albersUsa")
        .resolve_scale(color="independent")
        .properties(
            width=1080,
            # albersUsa's Alaska/Hawaii insets leave a fixed ~81px gap on the
            # left no matter the aspect ratio; 540 is the height where the
            # right-side fit gap comes closest to matching it (~80px), so the
            # map reads as centered/full-width instead of listing to one side.
            height=540,
            title=alt.Title(
                "Where is water stress concentrated?",
                subtitle=[
                    "Move the timeline to see how water stress may shift over time.",
                    "Baseline shows today's AI sites; ",
                    "Check the 'Show Proposed Data Centers' box to see where future data centers will be located.",
                ],
                anchor="start",
                # The map's own row needs no axis margin, but owner_bars/delta_chart
                # below it do (for their y-axis labels), so Vega-Lite's layout
                # naturally pushes this title well right of the row below.
                # Nudge it back so both titles share the same left edge
                # (tuned empirically; retune if row widths/padding change).
                dx=-151,
            ),
        )
    )

    owner_bars = (
        alt.Chart(sites)
        .transform_filter(site_filter)
        .transform_filter("datum.capacity_mw > 0")
        # Recompute the owner ranking for whatever region is brushed on the map.
        .transform_filter(map_brush)
        .transform_aggregate(
            total_capacity="sum(capacity_mw)",
            sites="count()",
            groupby=["operator", "site_type"],
        )
        .transform_window(
            owner_rank="rank()",
            sort=[alt.SortField("total_capacity", order="descending")],
        )
        .transform_filter("datum.owner_rank <= 12")
        .mark_bar(cornerRadiusEnd=3, cursor="pointer")
        .encode(
            y=alt.Y(
                "operator:N",
                sort="-x",
                title="Owner / operator",
                # minExtent locks the reserved label width so the chart's
                # left margin (and title position) don't shift as the
                # timeline changes which owner names are actually shown.
                axis=alt.Axis(labelLimit=130, minExtent=130),
            ),
            x=alt.X("total_capacity:Q", title="Total capacity (MW)"),
            color=owner_focus_color,
            opacity=alt.condition(owner_select, alt.value(1), alt.value(0.38)),
            tooltip=[
                alt.Tooltip("operator:N", title="Owner / operator"),
                alt.Tooltip("site_type:N", title="Site type"),
                alt.Tooltip("total_capacity:Q", title="Total capacity (MW)", format=",.0f"),
                alt.Tooltip("sites:Q", title="Sites"),
            ],
        )
        .properties(
            width=460,
            height=330,
            title=alt.Title(
                "Which owners control the most capacity?",
                subtitle=[
                    "Click an owner to highlight its locations on the map.",
                    "Drag a box on the map to rank owners within that region.",
                    "Note: Only sites on map are used in calculation. Make sure show proposed data centers is checked to include future sites"
                ],
                anchor="start",
            ),
        )
        .add_params(owner_select) # added show_future param for toggle switch
    )

    delta_data = (
        alt.Chart(comparison)
        .transform_calculate(
            selected_delta=f"{selected_projection('delta')}",
            selected_forecast=f"{selected_projection('future_score')}",
            selected_period=f"{period_label}",
            selected_scenario="'Business as usual'",
            absolute_change=f"abs({selected_projection('delta')})",
        )
        .transform_filter("water_step > 0 && isValid(datum.selected_delta)")
        .transform_window(
            change_rank="rank()",
            sort=[alt.SortField("absolute_change", order="descending")],
        )
        .transform_filter("datum.change_rank <= 12")
    )
    zero_rule = alt.Chart(pd.DataFrame({"zero": [0]})).mark_rule(
        color="#64748b", strokeWidth=1
    ).encode(x="zero:Q")
    delta_bars = delta_data.mark_bar(cornerRadiusEnd=3).encode(
        y=alt.Y(
            "name_1:N",
            sort="-x",
            title="State",
            # Same fixed-width trick: baseline renders zero rows here (no
            # bars until water_step > 0), so without a locked minExtent the
            # axis would collapse to ~0px at Baseline and jump wider at
            # 2030/2050/2080, shifting this chart's title each time.
            axis=alt.Axis(labelLimit=110, labelPadding=5, minExtent=110),
        ),
        x=alt.X(
            "selected_delta:Q",
            title="Forecast change from baseline",
            scale=alt.Scale(domain=[-1, 1], clamp=True),
        ),
        color=alt.Color(
            "selected_delta:Q",
            scale=alt.Scale(
                domain=[-1, 0, 1],
                range=["#2166ac", "#f7f7f7", "#b2182b"],
                clamp=True,
            ),
            legend=alt.Legend(
                title="Change in stress",
                orient="bottom",
                direction="horizontal",
                gradientLength=260,
            ),
        ),
        # Emphasize the bar for whichever state is hovered or pinned on the map,
        # tying the per-state delta view into the map's state selection.
        stroke=alt.condition(
            state_pin | state_hover, alt.value("#111827"), alt.value(None)
        ),
        strokeWidth=alt.condition(
            state_pin | state_hover, alt.value(1.6), alt.value(0)
        ),
        tooltip=[
            alt.Tooltip("name_1:N", title="State"),
            alt.Tooltip("baseline_score:Q", title="Baseline", format=".2f"),
            alt.Tooltip("selected_forecast:Q", title="Forecast", format=".2f"),
            alt.Tooltip("selected_delta:Q", title="Change", format="+.2f"),
            alt.Tooltip("selected_period:N", title="Period"),
            alt.Tooltip("selected_scenario:N", title="Scenario"),
        ],
    )
    delta_notice = (
        alt.Chart(
            pd.DataFrame({"message": ["Select 2030, 2050, or 2080 to view changes"]})
        )
        .transform_filter("water_step == 0")
        .mark_text(fontSize=13, color="#64748b", align="center")
        .encode(text="message:N")
    )
    delta_chart = (zero_rule + delta_bars + delta_notice).properties(
        width=460,
        height=330,
        title=alt.Title(
            "What changes most from today?",
            subtitle="The 12 largest absolute changes; red increases stress and blue decreases it.",
            anchor="start",
        ),
    )

    return (
        alt.vconcat(
            map_chart,
            alt.hconcat(owner_bars, delta_chart, spacing=24, center=False),
            spacing=36,
            center=False,
        )
        .add_params(period, show_future)
        .resolve_scale(color="independent")
        # Vega-Lite computes one shared canvas margin for the whole vconcat;
        # without this it's a hair too narrow for owner_bars' rotated axis
        # title, clipping it by ~1px. The minExtent locks on both bar
        # charts' y-axes do the real work now; this is just a small safety
        # margin (see map_chart's title dx for the actual alignment fix).
        .properties(padding={"left": 8, "top": 5, "right": 5, "bottom": 5})
    )


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
    shared_owner_scale = owner_scale(owners)
    owner_color_enc = alt.Color("owner_clean:N", scale=shared_owner_scale, title="Owner")
    brush = alt.selection_interval(encodings=['latitude', 'longitude'], fields=["Name"])
    brush_legend = alt.selection_point(fields=["owner_clean"], bind='legend')
    condition_legend = alt.when(brush_legend & brush).then(
        owner_color_enc
    ).otherwise(alt.value("grey"))
    # the map's Owner legend covers both views
    bar_condition = alt.when(brush & brush_legend).then(
        owner_color_enc.legend(None)
    ).otherwise(alt.value("grey"))

    company_bars = datacenters.site_concentration(df, lines=False).encode(color=bar_condition)

    points = (
        alt.Chart(df.dropna(subset=["Latitude", "Longitude"]))
        .mark_circle(opacity=0.7, stroke="white", strokeWidth=1)
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
