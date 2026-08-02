"""Structural tests for the unified AI economy explorer spec.

These assert on the *serialized* Vega-Lite spec rather than the Python objects,
because the behavior that matters here — one geographic brush shared by three
maps, one owner selection driving every view — is produced by Altair's
subchart parameter merge at ``to_dict()`` time, not by the builder calls.
"""

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


# --- The real explorer spec ------------------------------------------------

MAP_VIEWS = {"capital_sites", "electricity_sites", "water_sites"}


@pytest.fixture(scope="module")
def spec():
    return explorer.ai_economy_explorer().to_dict()


def test_explorer_builds_valid_spec(spec):
    assert "$schema" in spec


def test_one_geo_brush_shared_by_all_three_maps(spec):
    params = _params_by_name(spec)
    assert "geo_brush" in params
    assert set(params["geo_brush"]["views"]) == MAP_VIEWS


def test_state_selections_bind_to_the_water_choropleth(spec):
    """Attached to an enclosing concat these never fire — a concat has no marks
    to listen to — so they must land on the stress geoshape unit itself."""
    params = _params_by_name(spec)
    for name in ("water_state_hover", "water_state_pin"):
        assert params[name]["views"] == ["water_stress_states"]


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
    both the site filter and the brush filter have to run before the aggregate
    — filtering after it would only hide bars from a nationwide ranking."""
    bars = _find_view(spec, "owner_power_bars")
    assert bars is not None

    transforms = bars["transform"]
    aggregate_at = next(
        i for i, step in enumerate(transforms) if "aggregate" in step
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


def test_orientation_and_size_knobs_shape_the_layout():
    row = explorer.ai_economy_explorer(orientation="row", map_width=311).to_dict()
    column = explorer.ai_economy_explorer(orientation="column", map_width=311).to_dict()

    assert "hconcat" in row["vconcat"][0]
    assert "vconcat" in column["vconcat"][0]

    # The unit inherits its width from the enclosing layer's properties.
    assert _enclosing_width(row, "capital_sites") == 311


def test_orientation_rejects_unknown_values():
    with pytest.raises(ValueError):
        explorer.ai_economy_explorer(orientation="diagonal")


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
