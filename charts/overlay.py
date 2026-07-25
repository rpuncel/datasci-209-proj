"""Shared data center point-overlay layer for the choropleth maps.

Every map (water stress, electricity capacity, capital) draws the same circle
layer sized by a per-site magnitude. Centralizing it here means one place to
tune overlap legibility:

- **draw order** — rows are sorted largest-first so big marks render underneath
  smaller ones (Vega-Lite draws point marks in row order) and never bury them.
- **jitter** — if the frame carries ``lat_jit``/``lon_jit`` (from
  ``wrangle.jitter.jitter_overlaps``) those are plotted, spreading co-located
  stacks apart; otherwise the raw ``Latitude``/``Longitude`` are used, so this
  helper works with or without the jitter step.
- **opacity / stroke** — tunable so overlapping fills stay readable.

Passing ``jitter_controls=True`` instead ships each point's *unit offset*
(``dlat_unit``/``dlon_unit`` from ``wrangle.jitter``) to the browser and adds a
slider + checkbox so the jitter amount can be scaled live (needs an interactive
renderer). See ``jitter-lab.qmd``.
"""

import altair as alt

from wrangle.datacenters import POWER

# Single knob for how far a cluster's marks spread, in degrees. Applied by the
# map chart functions via wrangle.jitter so every map jitters consistently.
# Eye-tuned against the albersUsa pixel scale. This is the one control the
# in-browser slider scales live.
JITTER_SPREAD = 0.2

# How close two marks must be (degrees, single linkage) to count as the same
# cluster and get spread apart. 0 = only exact ZIP-centroid collisions; larger
# values also separate nearby-but-distinct metro sites whose big marks overlap.
# Clustering happens in pandas, so changing this needs a re-render (unlike the
# live spread slider).
CLUSTER_DIST = 0.35


def datacenter_points(
    df,
    size_field: str = POWER,
    *,
    size_title: str = "Power Capacity (MW)",
    size_range: tuple[float, float] = (20, 1000),
    tooltip: list | None = None,
    color=None,
    lat: str = "Latitude",
    lon: str = "Longitude",
    opacity: float = 0.7,
    stroke: str = "white",
    stroke_width: float = 0.6,
    jitter_controls: bool = False,
    **mark_kwargs,
) -> alt.Chart:
    """Build the circle overlay layer for a data center choropleth.

    Parameters
    ----------
    df : geocoded data center frame; ``lat_jit``/``lon_jit`` are used when
        present, else ``lat``/``lon``. With ``jitter_controls`` the frame must
        instead carry ``dlat_unit``/``dlon_unit`` (from ``jitter_unit_offsets``
        or ``jitter_overlaps``).
    size_field : column driving mark area (power, capex, compute, ...).
    size_title : legend title and default size tooltip label.
    size_range : ``[min, max]`` mark-area range for the size scale — tune per
        magnitude, since e.g. capex (USD billions) and power (MW) differ wildly.
    tooltip : override the default tooltip list.
    color : optional Altair color encoding/condition (e.g. an owner brush).
    opacity, stroke, stroke_width, **mark_kwargs : circle mark styling.
    jitter_controls : add a live slider (jitter amount) + checkbox (jitter on)
        that scale the unit offsets in the browser. Needs an interactive
        renderer.
    """
    plot_df = df.sort_values(size_field, ascending=False, kind="stable")

    if tooltip is None:
        tooltip = [
            "Name:N",
            "Address:N",
            alt.Tooltip(f"{size_field}:Q", title=size_title),
            alt.Tooltip("owner_clean:N", title="Owner"),
        ]

    encodings = dict(
        size=alt.Size(
            size_field,
            scale=alt.Scale(range=list(size_range)),
            legend=alt.Legend(title=size_title),
        ),
        tooltip=tooltip,
    )
    if color is not None:
        encodings["color"] = color

    mark = dict(opacity=opacity, stroke=stroke, strokeWidth=stroke_width, **mark_kwargs)

    if jitter_controls:
        missing = {"dlat_unit", "dlon_unit"} - set(plot_df.columns)
        if missing:
            raise ValueError(
                f"jitter_controls=True requires unit-offset columns {missing}; "
                "build the frame with wrangle.jitter.jitter_overlaps / "
                "jitter_unit_offsets first."
            )
        spread_param = alt.param(
            name="jitter_spread",
            value=JITTER_SPREAD,
            bind=alt.binding_range(min=0, max=0.6, step=0.01, name="Jitter amount (°) "),
        )
        enable_param = alt.param(
            name="jitter_on",
            value=True,
            bind=alt.binding_checkbox(name="Jitter on "),
        )
        # plotted coord = base + (on ? spread : 0) * unit offset, computed live
        scale = "(jitter_on ? jitter_spread : 0)"
        return (
            alt.Chart(plot_df)
            .transform_calculate(
                lon_plot=f"datum['{lon}'] + {scale} * datum.dlon_unit",
                lat_plot=f"datum['{lat}'] + {scale} * datum.dlat_unit",
            )
            .mark_circle(**mark)
            .encode(longitude="lon_plot:Q", latitude="lat_plot:Q", **encodings)
            .add_params(spread_param, enable_param)
        )

    lat_ch = "lat_jit" if "lat_jit" in plot_df.columns else lat
    lon_ch = "lon_jit" if "lon_jit" in plot_df.columns else lon
    return (
        alt.Chart(plot_df)
        .mark_circle(**mark)
        .encode(longitude=f"{lon_ch}:Q", latitude=f"{lat_ch}:Q", **encodings)
    )
