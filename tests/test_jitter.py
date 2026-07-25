"""Tests for the deterministic map-mark jitter helper."""

import math

import numpy as np
import pandas as pd

from wrangle.jitter import jitter_overlaps


def _colocated(n, lat=40.0, lon=-100.0, size_col=False):
    data = {"Latitude": [lat] * n, "Longitude": [lon] * n, "Name": list("ABCDEFGH"[:n])}
    if size_col:
        data["power"] = list(range(n, 0, -1))  # descending distinct sizes
    return pd.DataFrame(data)


def test_adds_jitter_columns():
    out = jitter_overlaps(_colocated(3))
    assert {"lat_jit", "lon_jit"} <= set(out.columns)


def test_singletons_untouched():
    df = pd.DataFrame(
        {"Latitude": [40.0, 30.0], "Longitude": [-100.0, -90.0], "Name": ["A", "B"]}
    )
    out = jitter_overlaps(df)
    assert out["lat_jit"].tolist() == df["Latitude"].tolist()
    assert out["lon_jit"].tolist() == df["Longitude"].tolist()


def test_colocated_points_become_distinct():
    out = jitter_overlaps(_colocated(4))
    coords = list(zip(out["lat_jit"], out["lon_jit"]))
    assert len(set(coords)) == len(coords)  # all pairwise distinct


def test_deterministic():
    df = _colocated(5)
    pd.testing.assert_frame_equal(jitter_overlaps(df), jitter_overlaps(df))


def test_largest_stays_at_centroid_when_sized():
    df = _colocated(4, lat=40.0, lon=-100.0, size_col=True)
    out = jitter_overlaps(df, size="power")
    biggest = out.loc[out["power"].idxmax()]
    assert biggest["lat_jit"] == 40.0
    assert biggest["lon_jit"] == -100.0


def test_offsets_within_spread():
    spread = 0.3
    lat, lon = 40.0, -100.0
    out = jitter_overlaps(_colocated(6, lat=lat, lon=lon), spread=spread)
    coslat = math.cos(math.radians(lat))
    for _, row in out.iterrows():
        dlat = row["lat_jit"] - lat
        dlon = (row["lon_jit"] - lon) * coslat  # undo longitude scaling
        assert math.hypot(dlat, dlon) <= spread + 1e-9


def test_nan_coordinates_pass_through():
    df = pd.DataFrame(
        {"Latitude": [40.0, np.nan], "Longitude": [-100.0, -90.0], "Name": ["A", "B"]}
    )
    out = jitter_overlaps(df)
    assert math.isnan(out.loc[1, "lat_jit"])
    # the valid singleton is unchanged
    assert out.loc[0, "lat_jit"] == 40.0


def test_distinct_locations_not_grouped():
    # two points ~50 km apart must not be treated as a stack
    df = pd.DataFrame(
        {"Latitude": [40.0, 40.5], "Longitude": [-100.0, -100.0], "Name": ["A", "B"]}
    )
    out = jitter_overlaps(df)
    assert out["lat_jit"].tolist() == [40.0, 40.5]
