"""Structural tests for the unified AI economy explorer spec.

These assert on the *serialized* Vega-Lite spec rather than the Python objects,
because the behavior that matters here — one geographic brush shared by three
maps, one owner selection driving every view — is produced by Altair's
subchart parameter merge at ``to_dict()`` time, not by the builder calls.
"""

import json
import re

import altair as alt
import pandas as pd
import pytest

from charts import explorer


@pytest.fixture(autouse=True)
def plain_data_transformer():
    """Validate specs with inline data, like charts/test_charts.py."""
    with alt.data_transformers.enable("default", max_rows=None):
        yield


def _params_by_name(spec: dict) -> dict:
    return {param["name"]: param for param in spec.get("params", [])}


# --- Spike: the mechanism the whole design rests on ------------------------
#
# Altair merges the *same* selection param object added to multiple named unit
# charts into a single top-level param whose ``views`` lists those unit names.
# ``LayerChart.add_params`` is the broken path (vega/altair#3891), so the param
# must be attached to the unit point chart *before* layering. If this ever
# stops holding, the explorer's shared brush silently degrades to per-map
# brushes and every other test here still passes.


def test_one_interval_param_merges_across_named_unit_views():
    frame = pd.DataFrame({"longitude": [-100.0, -80.0], "latitude": [40.0, 35.0]})
    brush = alt.selection_interval(name="geo_brush", encodings=["longitude", "latitude"])

    def points(name):
        return (
            alt.Chart(frame, name=name)
            .mark_point()
            .encode(longitude="longitude:Q", latitude="latitude:Q")
            .add_params(brush)
        )

    spec = alt.hconcat(points("map_a"), points("map_b")).to_dict()

    params = _params_by_name(spec)
    assert "geo_brush" in params, "brush did not lift to a single top-level param"
    assert set(params["geo_brush"]["views"]) == {"map_a", "map_b"}


def test_altair_still_misbinds_params_in_two_named_layer_subcharts():
    """Canary for the upstream bug ``_repair_shared_param_views`` exists to fix.

    Altair 6.2 loses which unit a param was added to when lifting it out of a
    layered concat subchart, so it binds the param to *every* named layer of
    that subchart (``_view_names_for_param``). With two named layers — our
    water map: choropleth for the state selections, points for the brush —
    that puts two units of one layer group in ``views``, and Vega rejects the
    spec with a duplicate signal name.

    When this test FAILS after an Altair upgrade, the inference has been fixed
    upstream: delete ``_repair_shared_param_views`` and ``_SHARED_PARAM_VIEWS``
    in charts/explorer.py and let Altair bind the views itself.
    """
    frame = pd.DataFrame({"longitude": [-100.0], "latitude": [40.0]})
    states = pd.DataFrame({"id": [6], "score": [3.0]})
    brush = alt.selection_interval(name="brush", encodings=["longitude", "latitude"])

    choropleth = alt.Chart(states, name="states").mark_geoshape().encode(color="score:Q")
    sites = (
        alt.Chart(frame, name="sites")
        .mark_point()
        .encode(longitude="longitude:Q", latitude="latitude:Q")
        .add_params(brush)
    )
    water_like = alt.layer(choropleth, sites).project(type="albersUsa")
    other = alt.Chart(frame, name="other").mark_point().encode(
        longitude="longitude:Q", latitude="latitude:Q"
    )

    spec = alt.hconcat(other, water_like).to_dict()

    views = set(_params_by_name(spec)["brush"]["views"])
    assert views == {"states_1", "sites_1"}, (
        "Altair no longer sweeps every named layer into the param's views — "
        "the workaround in explorer._repair_shared_param_views may be deletable"
    )


# --- The real explorer spec ------------------------------------------------


@pytest.fixture(scope="module")
def chart():
    return explorer.ai_economy_explorer()


@pytest.fixture(scope="module")
def spec(chart):
    return chart.to_dict()


@pytest.fixture(scope="module")
def emitted(chart):
    """Authored view name -> the name Vega actually emits.

    Altair 6.2 renames named units inside a layered concat subchart by
    appending the subchart's index, so these tests resolve names through the
    same mapping the explorer uses rather than hard-coding ``_0``/``_1``/``_2``.
    """
    return explorer._emitted_view_names(chart)


def test_emitted_names_cover_every_authored_view(emitted):
    """The repair looks every shared param's views up in this mapping, so a
    missing or misspelled entry would raise KeyError at build time — but a
    *stale* one would silently bind a param to nothing."""
    for name in (
        explorer.CAPITAL_SITES,
        explorer.ELECTRICITY_SITES,
        explorer.WATER_SITES,
        explorer.WATER_STATES,
        explorer.OWNER_BARS,
    ):
        assert name in emitted


def test_explorer_builds_valid_spec(spec):
    assert "$schema" in spec


def test_one_geo_brush_shared_by_all_three_maps(spec, emitted):
    params = _params_by_name(spec)
    assert "geo_brush" in params
    assert set(params["geo_brush"]["views"]) == {
        emitted[explorer.CAPITAL_SITES],
        emitted[explorer.ELECTRICITY_SITES],
        emitted[explorer.WATER_SITES],
    }


def test_state_selections_bind_to_the_water_choropleth(spec, emitted):
    """Attached to an enclosing concat these never fire — a concat has no marks
    to listen to — so they must land on the stress geoshape unit itself.

    They must also *not* spread to the site points sharing that layer: two
    units of one layer group duplicates the selection's signals and Vega
    rejects the spec, exactly as it does for the brush below."""
    params = _params_by_name(spec)
    for name in ("water_state_hover", "water_state_pin"):
        assert params[name]["views"] == [emitted[explorer.WATER_STATES]]


def _named_views(node, found=None):
    """Every view name in the spec, and the layer group each one belongs to.

    Returns ``{view_name: layer_group_id}``, where the id is ``None`` for views
    that are not inside a ``layer`` array.
    """
    found = {} if found is None else found

    def walk(node, group):
        if isinstance(node, dict):
            name = node.get("name")
            if isinstance(name, str) and not name.startswith("data-"):
                found[name] = group
            for key, value in node.items():
                walk(value, id(node["layer"]) if key == "layer" else group)
        elif isinstance(node, list):
            for item in node:
                walk(item, group)

    walk(node, None)
    return found


def test_every_param_view_names_a_real_view(spec):
    """A param pointing at a view that does not exist binds to nothing, and the
    interaction silently dies. Altair 6.2 leaves *stale* pre-rename names in
    ``views`` next to the renamed ones, so this is a live failure mode."""
    views = _named_views(spec["vconcat"])
    for param in spec["params"]:
        for view in param.get("views") or ():
            assert view in views, f"{param['name']} names missing view {view!r}"


def test_no_param_names_two_views_of_one_layer(spec):
    """The regression that broke the dashboard on Altair 6.2.

    A selection's signals are scoped to the enclosing layer group, so naming
    two units of the *same* layer emits them twice into one scope and Vega
    rejects the spec outright — ``Duplicate signal name: "geo_brush_tuple"``,
    and nothing renders. Altair's merge does exactly that: it binds a layer
    subchart's param to every named layer, sweeping the water choropleth in
    alongside its site points.

    Both ``geo_brush`` and the two water state selections hit this, so assert
    it for every param rather than just the brush that happens to fail first.
    """
    views = _named_views(spec["vconcat"])
    for param in spec["params"]:
        groups = [views[v] for v in param.get("views") or () if views.get(v)]
        assert len(groups) == len(set(groups)), (
            f"{param['name']} names two views of one layer group — "
            "Vega will fail with a duplicate signal name"
        )


def test_owner_select_is_owned_by_the_bar_chart(spec):
    params = _params_by_name(spec)
    assert "owner_select" in params
    assert params["owner_select"]["select"]["fields"] == ["owner_clean"]
    assert params["owner_select"]["views"] == ["owner_power_bars"]


def test_timeline_and_checkbox_params_keep_their_contract_names(spec):
    """``water_step`` is hard-coded in charts/_theme.py's JS button rewrite and
    ``show_future_sites`` in the site filter expression; renaming either
    silently breaks the timeline buttons or the proposed-sites toggle."""
    params = _params_by_name(spec)

    step = params["water_step"]
    assert step["bind"]["input"] == "range"
    assert (step["bind"]["min"], step["bind"]["max"]) == (0, 3)

    assert params["show_future_sites"]["bind"]["input"] == "checkbox"


def _find_view(node, name):
    """Depth-first search for a named unit view anywhere in a concat/layer tree."""
    if isinstance(node, dict):
        if node.get("name") == name:
            return node
        for value in node.values():
            found = _find_view(value, name)
            if found is not None:
                return found
    elif isinstance(node, list):
        for item in node:
            found = _find_view(item, name)
            if found is not None:
                return found
    return None


def test_brush_filters_owner_bars_upstream_of_the_aggregate(spec):
    """The top-12 ranking must genuinely recompute for the brushed region, so
    both the site filter and the brush filter have to run before the
    owner-level rollup — filtering after it would only hide bars from a
    nationwide ranking. The rollup is a ``joinaggregate`` (not an
    ``aggregate``) because it annotates each site row rather than collapsing
    them, which is what lets the bars stack one segment per data center."""
    bars = _find_view(spec, "owner_power_bars")
    assert bars is not None

    transforms = bars["transform"]
    aggregate_at = next(
        i for i, step in enumerate(transforms) if "joinaggregate" in step
    )
    brush_at = next(
        i
        for i, step in enumerate(transforms)
        if isinstance(step.get("filter"), dict)
        and step["filter"].get("param") == "geo_brush"
    )
    site_filter_at = next(
        i
        for i, step in enumerate(transforms)
        if isinstance(step.get("filter"), str) and "show_future_sites" in step["filter"]
    )

    assert site_filter_at < aggregate_at
    assert brush_at < aggregate_at


_MISSING = object()


def _rendered_legends(node, channel):
    """Every channel definition that will actually draw a legend.

    Note the asymmetry that makes this worth a helper: ``"legend": null``
    suppresses a legend, but an *absent* ``legend`` key means Vega-Lite
    generates a default one. Treating "absent" as "no legend" would let three
    duplicate size legends slip through these tests.
    """
    found = []
    if isinstance(node, dict):
        encoding = node.get("encoding", {})
        if isinstance(encoding, dict) and channel in encoding:
            for channel_def in _channel_defs(encoding[channel]):
                if channel_def.get("legend", _MISSING) is not None:
                    found.append(channel_def)
        for key, value in node.items():
            if key != "encoding":
                found.extend(_rendered_legends(value, channel))
    elif isinstance(node, list):
        for item in node:
            found.extend(_rendered_legends(item, channel))
    return found


def _channel_defs(channel_def):
    """A channel may be a plain definition or an alt.condition wrapper."""
    if not isinstance(channel_def, dict):
        return []
    defs = []
    if "field" in channel_def:
        defs.append(channel_def)
    condition = channel_def.get("condition")
    if isinstance(condition, dict) and "field" in condition:
        defs.append(condition)
    elif isinstance(condition, list):
        defs.extend(c for c in condition if isinstance(c, dict) and "field" in c)
    return defs


def test_owner_bars_are_the_only_owner_legend(spec):
    """The bar chart *is* the owner legend. The data carries ~200 distinct
    operators, so a real categorical color legend would be unusable and would
    duplicate what the ranking already shows."""
    owner_legends = [
        c for c in _rendered_legends(spec, "color") if c.get("field") == "owner_clean"
    ]
    assert owner_legends == []


def test_single_shared_size_and_shape_legends(spec):
    """Three maps drawing the same site layer must not each print their own
    capacity and site-layer legends."""
    size_legends = _rendered_legends(spec, "size")
    assert len(size_legends) == 1, "expected exactly one shared capacity size legend"
    assert size_legends[0]["field"] == "capacity_mw"

    shape_legends = _rendered_legends(spec, "shape")
    assert len(shape_legends) == 1
    assert shape_legends[0]["field"] == "site_type"


def test_maps_resolve_size_and_shape_independently(spec):
    """Without this, Vega-Lite merges the three maps' size/shape scales, the
    sibling ``legend: null``s suppress the merged shape legend outright, and
    the capacity legend is hoisted to the root group — rendering at the very
    bottom of the page rather than beneath the maps it describes."""
    maps = spec["vconcat"][0]
    resolve = maps["resolve"]["scale"]
    assert resolve["size"] == "independent"
    assert resolve["shape"] == "independent"


def test_orientation_and_size_knobs_shape_the_layout(emitted):
    row = explorer.ai_economy_explorer(orientation="row", map_width=311).to_dict()
    column = explorer.ai_economy_explorer(orientation="column", map_width=311).to_dict()

    assert "hconcat" in row["vconcat"][0]
    assert "vconcat" in column["vconcat"][0]

    # The unit inherits its width from the enclosing layer's properties.
    assert _enclosing_width(row, emitted[explorer.CAPITAL_SITES]) == 311


def test_orientation_rejects_unknown_values():
    with pytest.raises(ValueError):
        explorer.ai_economy_explorer(orientation="diagonal")


# The floor we size for is a 1536 CSS px viewport: a 1920x1080 Windows laptop
# at the default 125% display scaling reports exactly 1536 CSS px, and MacBook
# logical widths (~1440-1512) are close enough that they fall back gracefully to
# the styles.css horizontal scroller. Measured from the rendered dashboard, the
# explorer card's content box is about (viewport - 120) px, so 1536 leaves
# 1416px. Beyond that the card scrolls and the third map is clipped.
CARD_WIDTH_AT_1536 = 1416


def test_rendered_width_fits_the_dashboard_card():
    """The explorer's total width is only loosely related to MAP_WIDTH.

    Each map's bottom legend row can be *wider* than the map and overhang to the
    right, and Vega reserves the owner bars' y-axis extent as a left gutter on
    every row of the concat. Both are easy to inflate by accident — a longer
    legend title or a bigger ``minExtent`` costs real map width — and the
    symptom (a horizontal scrollbar on a 1536px laptop) is invisible from the
    spec alone. So render it and measure.

    Both interactive states are gated: checking "show proposed data centers"
    widens the shape legend and adds ~16px, so the default state fitting is not
    on its own enough.
    """
    vlc = pytest.importorskip("vl_convert")
    spec = explorer.ai_economy_explorer().to_dict()

    def rendered_width(spec_dict) -> int:
        svg = vlc.vegalite_to_svg(json.dumps(spec_dict))
        return int(re.search(r'width="(\d+)"', svg).group(1))

    default_width = rendered_width(spec)

    show_future = _params_by_name(spec)["show_future_sites"]
    show_future["value"] = True
    checked_width = rendered_width(spec)

    for state, width in (("default", default_width), ("checkbox on", checked_width)):
        assert width <= CARD_WIDTH_AT_1536, (
            f"explorer renders {width}px wide in the {state} state, over the "
            f"{CARD_WIDTH_AT_1536}px card. Shrink MAP_WIDTH (3px of total per "
            "1px of map), a legend (title or gradientLength), or the owner "
            "bars' y-axis minExtent."
        )


def _enclosing_width(node, view_name):
    """Width of the nearest ancestor (or self) carrying an explicit width."""
    if isinstance(node, dict):
        if _find_view(node, view_name) is not None:
            for value in node.values():
                nested = _enclosing_width(value, view_name)
                if nested is not None:
                    return nested
            return node.get("width")
    elif isinstance(node, list):
        for item in node:
            found = _enclosing_width(item, view_name)
            if found is not None:
                return found
    return None


def test_spec_serializes_without_pre_transform():
    """charts.interactive() re-serializes with pre_transform disabled so the
    browser runs the transforms; that path has its own vegafusion codepath and
    has broken independently of plain to_dict() before."""
    spec = explorer.ai_economy_explorer().to_dict(context={"pre_transform": False})
    assert "$schema" in spec
