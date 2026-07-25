"""Spec-level tests for the shared data center point-overlay helper."""

import altair as alt
import pandas as pd
import pytest

from charts.overlay import datacenter_points
from wrangle.datacenters import POWER


def _frame(with_jitter=False):
    df = pd.DataFrame(
        {
            "Name": ["A", "B", "C"],
            "Address": ["a", "b", "c"],
            "owner_clean": ["X", "Y", "Z"],
            "Latitude": [40.0, 41.0, 42.0],
            "Longitude": [-100.0, -101.0, -102.0],
            POWER: [10.0, 300.0, 100.0],
        }
    )
    if with_jitter:
        df["lat_jit"] = df["Latitude"] + 0.01
        df["lon_jit"] = df["Longitude"] - 0.01
    return df


def test_returns_chart_with_valid_spec():
    chart = datacenter_points(_frame())
    spec = chart.to_dict()  # raises if the spec is invalid
    assert spec["mark"]["type"] == "circle"


def test_uses_raw_coords_without_jitter():
    spec = datacenter_points(_frame()).to_dict()
    assert spec["encoding"]["longitude"]["field"] == "Longitude"
    assert spec["encoding"]["latitude"]["field"] == "Latitude"


def test_prefers_jitter_columns_when_present():
    spec = datacenter_points(_frame(with_jitter=True)).to_dict()
    assert spec["encoding"]["longitude"]["field"] == "lon_jit"
    assert spec["encoding"]["latitude"]["field"] == "lat_jit"


def test_draw_order_biggest_first():
    chart = datacenter_points(_frame())
    powers = [row[POWER] for row in chart.data.to_dict("records")]
    assert powers == sorted(powers, reverse=True)  # big drawn first (underneath)


def test_color_encoding_optional():
    assert "color" not in datacenter_points(_frame()).to_dict()["encoding"]
    colored = datacenter_points(_frame(), color=alt.Color("owner_clean:N"))
    assert "color" in colored.to_dict()["encoding"]


def _frame_with_units():
    df = _frame()
    df["dlat_unit"] = [0.0, 0.0, 0.0]
    df["dlon_unit"] = [0.0, 0.0, 0.0]
    return df


def test_jitter_controls_adds_params_and_calc():
    spec = datacenter_points(_frame_with_units(), jitter_controls=True).to_dict()
    param_names = {p["name"] for p in spec.get("params", [])}
    assert {"jitter_spread", "jitter_on"} <= param_names
    # coordinates come from the calculated fields, not raw columns
    assert spec["encoding"]["longitude"]["field"] == "lon_plot"
    assert spec["encoding"]["latitude"]["field"] == "lat_plot"
    calc_targets = {t["as"] for t in spec["transform"]}
    assert {"lon_plot", "lat_plot"} <= calc_targets


def test_jitter_controls_requires_unit_columns():
    with pytest.raises(ValueError, match="unit-offset columns"):
        datacenter_points(_frame(), jitter_controls=True)
