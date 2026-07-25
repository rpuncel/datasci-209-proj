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
"""

import altair as alt

from wrangle.datacenters import POWER


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
    **mark_kwargs,
) -> alt.Chart:
    """Build the circle overlay layer for a data center choropleth.

    Parameters
    ----------
    df : geocoded data center frame; ``lat_jit``/``lon_jit`` are used when
        present, else ``lat``/``lon``.
    size_field : column driving mark area (power, capex, compute, ...).
    size_title : legend title and default size tooltip label.
    size_range : ``[min, max]`` mark-area range for the size scale — tune per
        magnitude, since e.g. capex (USD billions) and power (MW) differ wildly.
    tooltip : override the default tooltip list.
    color : optional Altair color encoding/condition (e.g. an owner brush).
    opacity, stroke, stroke_width, **mark_kwargs : circle mark styling.
    """
    plot_df = df.sort_values(size_field, ascending=False, kind="stable")

    lat_ch = "lat_jit" if "lat_jit" in plot_df.columns else lat
    lon_ch = "lon_jit" if "lon_jit" in plot_df.columns else lon

    if tooltip is None:
        tooltip = [
            "Name:N",
            "Address:N",
            alt.Tooltip(f"{size_field}:Q", title=size_title),
            alt.Tooltip("owner_clean:N", title="Owner"),
        ]

    encodings = dict(
        longitude=f"{lon_ch}:Q",
        latitude=f"{lat_ch}:Q",
        size=alt.Size(
            size_field,
            scale=alt.Scale(range=list(size_range)),
            legend=alt.Legend(title=size_title),
        ),
        tooltip=tooltip,
    )
    if color is not None:
        encodings["color"] = color

    return (
        alt.Chart(plot_df)
        .mark_circle(
            opacity=opacity, stroke=stroke, strokeWidth=stroke_width, **mark_kwargs
        )
        .encode(**encodings)
    )
