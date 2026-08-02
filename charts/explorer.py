"""Unified, owner-linked "AI economy" explorer.

Three choropleths — capital, grid capacity, water stress — plus one owner
ranking and one per-state water-change chart, assembled into a *single* Altair
spec. That is the whole point: Vega selections cannot cross vega-embed
instances, so rendering these as separate ``charts.interactive()`` cells (as
the dashboard used to) leaves every view interactively isolated. In one spec:

- clicking a bar in the owner ranking highlights that owner's sites on all
  three maps;
- one "show proposed data centers" checkbox drives all three site overlays and
  the owner ranking;
- one geographic brush, draggable on *any* of the three maps, filters the owner
  ranking upstream of its aggregate, so the top-12 genuinely re-ranks for the
  brushed region rather than just hiding bars;
- the water timeline, state hover/pin, and per-state delta chart come along via
  the layer builders in ``charts.water``.

Render with::

    charts.interactive(ai_economy_explorer(), id="ai-economy-explorer")

Layout is meant to be tweaked: pass ``orientation``/``map_width``/... or edit
the module constants below.
"""

import altair as alt
import pandas as pd

from charts import electricity, money, water, datacenters
from charts.owner_colors import owner_scale

from wrangle import water as ww

# Layout knobs, in one place. Three albersUsa maps sit side by side at these
# dimensions, inside a dashboard card that offers roughly (viewport - 120) px.
#
# The width the explorer actually renders at was measured against Altair 6.2.2
# with vl_convert, and over the whole usable range it is linear in MAP_WIDTH:
#
#     total = 3 * MAP_WIDTH + 70 + minExtent            (default state)
#     total = 3 * MAP_WIDTH + 70 + minExtent + 16       ("show proposed sites")
#
# where minExtent is the owner bars' y-axis gutter (see the axis at line ~276).
# Vega lays the outer concat out with bounds "full", so that gutter is reserved
# on *every* row and shifts the whole spec right by it; `align: "none"` does not
# opt out. The constant 70 is the two 18px map gaps, 13px of root padding, and
# ~21px of axis-title overhead. Because the relationship is exactly 3px of total
# per 1px of map, no map's bottom legend row currently overhangs its map — the
# legends cost nothing at these sizes, and the checkbox-on state is the +16px
# worst case the width test has to clear.
#
# The budget is a 1536px viewport floor (a 1920x1080 Windows laptop at the
# default 125% scaling reports 1536 CSS px; MacBook logical widths sit at
# 1440-1512 and degrade to the styles.css horizontal scroller). The card offers
# about (viewport - 120) px, so 1416px is the ceiling: 3*410 + 70 + 90 = 1390
# default, 1406 with the checkbox on.
#
# To readjust: change MAP_WIDTH (MAP_HEIGHT follows from it), keep BAR_WIDTH at
# or below (3*MAP_WIDTH - 260)/2 so the bottom row never becomes the widest one,
# and run charts/test_explorer.py::test_rendered_width_fits_the_dashboard_card.
# Red prints the rendered width; every 3px over costs 1px of MAP_WIDTH.
MAP_WIDTH = 600
# albersUsa auto-fits to the view with no explicit scale, so the projection's
# native ~1.72:1 aspect is what decides how tall a map needs to be. Deriving the
# height keeps the two in step, and the +2 leaves width the binding constraint
# rather than height; anything taller is dead space below the geometry.
MAP_ASPECT = 1.72
MAP_HEIGHT = round(MAP_WIDTH / MAP_ASPECT) + 2
# Sized so the bottom row (bars + their axis gutter, then the delta chart) comes
# out about as wide as the maps row above it.
BAR_WIDTH = 540
BAR_HEIGHT = 330
MAP_SPACING = 18
ROW_SPACING = 30
BOTTOM_SPACING = 24

# Grey for marks whose owner is not currently selected.
DIM_COLOR = "#cbd5e1"

# How many owners the ranking keeps.
OWNER_RANK_LIMIT = 12

# Baseline sites always show; proposed projects only when the checkbox is on.
SITE_FILTER = (
    "datum.site_period == 'Baseline' || "
    "(datum.site_period == 'Future' && show_future_sites)"
)

# Authored unit-view names. These are load-bearing twice over: Altair merges the
# shared params into top-level params listing them in `views`, and Vega emits
# each as an SVG group class that driver_config.js hooks (`owner_power_bars`).
# charts/test_explorer.py pins them.
#
# Note these are the names we *write*, not always the ones Vega emits: Altair
# 6.2 appends a position suffix to named units inside a layered concat subchart.
# Use _emitted_view_names() to resolve one to the other.
CAPITAL_SITES = "capital_sites"
ELECTRICITY_SITES = "electricity_sites"
WATER_SITES = "water_sites"
WATER_STATES = "water_stress_states"
OWNER_BARS = "owner_power_bars"

# Which views each param that crosses a layer boundary is supposed to drive.
# Only these need declaring: `owner_select` lives on the bars, a direct concat
# child, which Altair names correctly on its own. See
# _repair_shared_param_views() for what it gets wrong about the rest.
_SHARED_PARAM_VIEWS = {
    "geo_brush": (CAPITAL_SITES, ELECTRICITY_SITES, WATER_SITES),
    "water_state_hover": (WATER_STATES,),
    "water_state_pin": (WATER_STATES,),
}

# capacity_mw is heavily right-skewed (most sites sit far below the 7000 MW
# max), so a linear scale would crowd nearly every point into the smallest
# sliver of the size range. sqrt spreads out that common low end at the cost of
# some separation among the rare, very large outliers.
_SIZE_SCALE = alt.Scale(range=[16, 3000], clamp=True)
_SHAPE_SCALE = alt.Scale(
    domain=["Current AI site", "Proposed project"],
    range=["circle", "triangle-up"],
)


def _site_points(
    sites: pd.DataFrame,
    *,
    name: str,
    owner_focus_color,
    owner_select,
    geo_brush,
    extra_tooltip=(),
    size_legend=None,
    shape_legend=None,
) -> alt.Chart:
    """One map's data center overlay, and one of the shared brush's sources.

    ``geo_brush`` is added here, on the *unit* chart, rather than on the
    enclosing layer: ``LayerChart.add_params`` is silently dropped by Altair's
    subchart parameter merge (vega/altair#3891). Adding the same param object
    to each map's unit chart is what makes Altair lift it to a single top-level
    param whose ``views`` names all three maps — i.e. one brush, three maps.
    Altair infers those view names badly, so ``_repair_shared_param_views``
    fixes them up once the whole chart is assembled.

    All three maps size by ``capacity_mw`` rather than by their own quantity:
    capex and H100 equivalents are NaN on proposed rows, so a capex-sized mark
    simply would not render once the checkbox is on.
    """
    tooltip = [
        alt.Tooltip("site_name:N", title="Site"),
        alt.Tooltip("site_type:N", title="Type"),
        alt.Tooltip("owner_clean:N", title="Owner / operator"),
        alt.Tooltip("address:N", title="Address"),
        alt.Tooltip("capacity_mw:Q", title="Site capacity (MW)", format=",.0f"),
        *extra_tooltip,
    ]
    return (
        alt.Chart(sites, name=name)
        .transform_filter(SITE_FILTER)
        .transform_filter("datum.capacity_mw > 0")
        .mark_point(filled=True, stroke="#ffffff", strokeWidth=0.7)
        .encode(
            longitude="longitude:Q",
            latitude="latitude:Q",
            size=alt.Size("capacity_mw:Q", scale=_SIZE_SCALE, legend=size_legend),
            color=owner_focus_color,
            shape=alt.Shape("site_type:N", scale=_SHAPE_SCALE, legend=shape_legend),
            opacity=alt.condition(
                owner_select & geo_brush, alt.value(0.95), alt.value(0.22)
            ),
            tooltip=tooltip,
        )
        .add_params(geo_brush)
    )


def _emitted_view_names(chart, found=None) -> dict[str, str]:
    """Map each authored unit-view name to the name Vega will actually emit.

    Altair 6.2 disambiguates named units inside a layered concat subchart by
    appending the subchart's index, so ``capital_sites`` reaches Vega as
    ``capital_sites_0`` and the water map's two named layers become
    ``water_stress_states_2`` and ``water_sites_2``. ``to_dict()`` re-applies
    the rename every time and it is idempotent, so it cannot be undone by
    mutating the chart — the names already on the built object are the emitted
    ones, and reading them back is what keeps the suffix out of this module.

    Names that Altair leaves alone (``owner_power_bars``, a direct concat
    child) simply map to themselves, as they would if a future Altair dropped
    the rename entirely.
    """
    found = {} if found is None else found
    if isinstance(chart, alt.Chart) and isinstance(chart.name, str):
        base, _, suffix = chart.name.rpartition("_")
        found[base if base and suffix.isdigit() else chart.name] = chart.name
    for attr in ("layer", "hconcat", "vconcat", "concat"):
        for subchart in getattr(chart, attr, None) or ():
            _emitted_view_names(subchart, found)
    return found


def _repair_shared_param_views(chart: alt.VConcatChart) -> alt.VConcatChart:
    """Pin each shared param to exactly the views it is supposed to drive.

    Altair 6.2's ``_combine_subchart_params`` infers the wrong ``views`` for
    every param the explorer shares across subcharts, in two ways:

    * ``_view_names_for_param`` returns *every* named layer of a ``LayerChart``
      subchart, not just the layer the param was added to. So ``geo_brush``,
      added only to the site points, also lands on the water choropleth — and a
      param naming two units of one layer group has its signals emitted twice
      into that one scope, which Vega rejects outright: ``Duplicate signal
      name: "geo_brush_tuple"``, and the dashboard renders nothing. The water
      state hover/pin are hit the same way (they pick up the site points), so
      the spec carries two instances of the fault; only the first is visible,
      because parsing stops there.
    * the merge branch keeps the pre-rename views alongside the renamed ones,
      leaving stale entries like ``water_sites`` next to ``water_sites_2``.
      Vega-Lite ignores those, but they make the spec a poor thing to debug.

    The correct bindings are fixed and few, so declare them in
    ``_SHARED_PARAM_VIEWS`` and overwrite whatever Altair inferred.
    """
    emitted = _emitted_view_names(chart)
    for param in chart.params:
        bases = _SHARED_PARAM_VIEWS.get(getattr(param, "name", None))
        if bases is not None:
            param.views = [emitted[base] for base in bases]
    return chart


def _map(*layers, **kwargs) -> alt.LayerChart:
    """Choropleth base + site overlay as one projected, independently-scaled map."""
    return (
        alt.layer(*layers)
        .project(type="albersUsa")
        # The choropleth's sequential fill and the points' categorical owner
        # palette are different color scales sharing one view.
        .resolve_scale(color="independent")
        .properties(**kwargs)
    )


def _owner_bars(
    sites: pd.DataFrame,
    *,
    owner_focus_color,
    owner_select,
    geo_brush,
    width: int,
    height: int,
) -> alt.Chart:
    """The owner ranking, which doubles as the explorer's owner legend.

    Both the site filter and the brush filter run *before* the aggregate, so
    brushing a region genuinely recomputes the top-N for that region instead of
    hiding bars from a fixed nationwide ranking. ``charts/test_explorer.py``
    pins that ordering.
    """
    return (
        alt.Chart(sites, name=OWNER_BARS)
        .transform_filter(SITE_FILTER)
        .transform_filter("datum.capacity_mw > 0")
        .transform_filter(geo_brush)
        .transform_aggregate(
            total_capacity="sum(capacity_mw)",
            sites="count()",
            groupby=["owner_clean", "site_type"],
        )
        .transform_window(
            owner_rank="rank()",
            sort=[alt.SortField("total_capacity", order="descending")],
        )
        .transform_filter(f"datum.owner_rank <= {OWNER_RANK_LIMIT}")
        .mark_bar(cornerRadiusEnd=3, cursor="pointer")
        .encode(
            y=alt.Y(
                "owner_clean:N",
                sort="-x",
                title="Owner / operator",
                # minExtent locks the reserved label width so the chart's left
                # margin (and title position) don't shift as the timeline or
                # brush changes which owner names are shown. It is also a left
                # gutter on every row of the outer concat, so it trades against
                # map width 1:1 — 90px clears every top-12 owner name in the
                # default Baseline ranking and only truncates the long proposed
                # -project owners, which 130 was already truncating. Tooltips
                # still carry the full name.
                axis=alt.Axis(labelLimit=90, minExtent=90),
            ),
            x=alt.X("total_capacity:Q", title="Total capacity (MW)"),
            color=owner_focus_color,
            opacity=alt.condition(owner_select, alt.value(1), alt.value(0.38)),
            tooltip=[
                alt.Tooltip("owner_clean:N", title="Owner / operator"),
                alt.Tooltip("site_type:N", title="Site type"),
                alt.Tooltip(
                    "total_capacity:Q", title="Total capacity (MW)", format=",.0f"
                ),
                alt.Tooltip("sites:Q", title="Sites"),
            ],
        )
        .properties(
            width=width,
            height=height,
            title=alt.Title(
                "Which owners control the most capacity?",
                subtitle=[
                    "Click an owner to highlight its sites on all three maps.",
                    "Drag a box on any map to rank owners within that region.",
                ],
                anchor="start",
            ),
        )
        .add_params(owner_select)
    )

def _site_concentration(owner_select, geo_brush, sites: pd.DataFrame, color: alt.Color | None) -> alt.LayerChart:
    site_bars = (
        alt.Chart(sites,name="site_bars").mark_bar().encode(
            y=alt.Y("rank:O", title="Site rank by current power"),
            x=alt.X("capacity_mw:Q", title="Capacity (MW)"),
            color=color,
            tooltip=[
                alt.Tooltip("rank:O", title="Rank"),
                alt.Tooltip("Name:N", title="Data center"),
                alt.Tooltip("owner_clean:N", title="Owner"),
                alt.Tooltip("capacity_mw:Q", title="Power (MW)", format=",.0f"),
                alt.Tooltip("Country:N", title="Country"),
            ],
        )
        .add_params(owner_select)
        .transform_filter(SITE_FILTER)
        .transform_filter("datum.capacity_mw > 0")
        .transform_filter(geo_brush)
        .transform_window(
            rank='row_number()',
            sort=[alt.SortField("capacity_mw", order="descending")],
        )
        .transform_filter(
            alt.datum.rank < 10
        )
    )
    return  site_bars.properties(
        title=alt.Title(
            "A few large sites account for much of the current footprint",
            #subtitle=f"The top 10 sites represent {dc.stats().top10_power_share:.1%} of estimated current power.",
            anchor="start",
        ),
        height=390,
    )



def ai_economy_explorer(
    sites: pd.DataFrame | None = None,
    *,
    orientation: str = "row",
    map_width: int = MAP_WIDTH,
    map_height: int = MAP_HEIGHT,
    bar_width: int = BAR_WIDTH,
    bar_height: int = BAR_HEIGHT,
) -> alt.VConcatChart:
    """Assemble the linked maps + owner ranking + water delta chart.

    ``sites`` defaults to ``wrangle.water.explorer_sites()``. ``orientation``
    puts the three maps in a row (default) or a column.
    """
    if orientation not in ("row", "column"):
        raise ValueError("orientation must be 'row' or 'column'")
    if sites is None:
        sites = ww.explorer_sites()

    period = water.water_step_param()
    show_future = water.show_future_sites_param()
    state_hover, state_pin = water.state_selections()

    owner_select = alt.selection_point(
        name="owner_select",
        fields=["owner_clean"],
        on="click",
        clear="dblclick",
        empty=True,
    )
    # One interval selection object, added to all three maps' point units below.
    # Altair merges it into a single top-level param (emitting a benign
    # "Automatically deduplicated selection parameter" warning), which is what
    # makes a drag on any map drive the same brush.
    geo_brush = alt.selection_interval(
        name="geo_brush",
        encodings=["longitude", "latitude"],
        empty=True,
    )

    # The bars ARE the owner legend, so there is no separate color legend: the
    # data carries ~200 distinct operators, which would make an unusable one,
    # and the ranking already shows who is who.
    owner_focus_color = alt.condition(
        owner_select,
        alt.Color(
            "owner_clean:N", scale=owner_scale(sites["owner_clean"]), legend=None
        ),
        alt.value(DIM_COLOR),
    )

    def points(name, **kwargs):
        return _site_points(
            sites,
            name=name,
            owner_focus_color=owner_focus_color,
            owner_select=owner_select,
            geo_brush=geo_brush,
            **kwargs,
        )

    capital_map = _map(
        money.capital_choropleth(
            # This legend and the capacity legend below sit side by side under
            # the first map. Both the short title and the short gradient are
            # there to keep that pair inside MAP_WIDTH: at the current sizes no
            # legend row overhangs its map, so the maps alone set the total SVG
            # width, but a legend that outgrows its map starts adding width
            # again. See the layout note at the top of this module.
            legend=alt.Legend(
                title="Capital (USD B)",
                orient="bottom",
                direction="horizontal",
                gradientLength=110,
            )
        ),
        points(
            CAPITAL_SITES,
            extra_tooltip=[
                alt.Tooltip("capex_b:Q", title="Capital (USD B)", format=",.1f")
            ],
            # The single capacity legend. Its siblings pass legend=None, which
            # only works because the maps concat resolves size independently:
            # under Vega-Lite's default shared resolution the three size scales
            # merge, the sibling nulls suppress the merged legend, and it lands
            # on the root group at the very bottom of the page instead of here.
            size_legend=alt.Legend(
                title="Site capacity (MW)",
                orient="bottom",
                direction="horizontal",
                values=[100, 600, 1800, 3000],
            ),
        ),
        width=map_width,
        height=map_height,
        title="💰 Capital invested",
    )

    electricity_map = _map(
        electricity.electricity_capacity_choropleth(),
        points(
            ELECTRICITY_SITES,
            extra_tooltip=[
                alt.Tooltip("h100_eq:Q", title="H100 equivalents", format=",.0f")
            ],
        ),
        width=map_width,
        height=map_height,
        title="⚡ Grid capacity",
    )

    no_data, stress = water.stress_timeline_layers(
        state_hover,
        state_pin,
        name=WATER_STATES,
        # The standalone explorer's full-sentence legend title is wider than a
        # map is here. This legend also shares its row with the site-shape
        # legend below, so the pair has to stay inside MAP_WIDTH.
        legend=alt.Legend(
            title="Water stress (0-5)",
            orient="bottom",
            direction="horizontal",
            gradientLength=140,
        ),
    )
    water_map = _map(
        no_data,
        stress,
        points(
            WATER_SITES,
            # The one shared site-layer legend; only this map needs to explain
            # the circle/triangle distinction the checkbox introduces.
            shape_legend=alt.Legend(
                title="Site layer",
                orient="bottom",
                direction="horizontal",
                # Default legend symbols render tiny next to the size-encoded
                # marks; bump them up so the shapes are actually legible.
                symbolSize=200,
            ),
        ),
        width=map_width,
        height=map_height,
        title="💧 Water stress",
    )

    combine = alt.hconcat if orientation == "row" else alt.vconcat
    maps = combine(
        capital_map, electricity_map, water_map, spacing=MAP_SPACING
    ).resolve_scale(size="independent", shape="independent")

    bottom = alt.hconcat(
        _owner_bars(
            sites,
            owner_focus_color=owner_focus_color,
            owner_select=owner_select,
            geo_brush=geo_brush,
            width=bar_width,
            height=bar_height,
        ),
        _site_concentration(owner_select, geo_brush, sites=sites, color=owner_focus_color),
        water.stress_delta_chart(
            state_hover, state_pin, width=bar_width, height=bar_height
        ),
        spacing=BOTTOM_SPACING,
        center=False,
    )

    chart = (
        alt.vconcat(maps, bottom, spacing=ROW_SPACING, center=False)
        .add_params(period, show_future)
        .resolve_scale(color="independent")
        .properties(padding={"left": 8, "top": 5, "right": 5, "bottom": 5})
    )
    return _repair_shared_param_views(chart)
