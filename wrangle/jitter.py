"""Deterministic jitter for co-located map marks.

U.S. data centers are placed at ZIP-code centroids (see ``wrangle.water``), so
every site sharing a ZIP lands on the *exact same* coordinate and its mark
stacks perfectly on its neighbors. This module spreads each such stack onto a
small golden-angle spiral around its shared centroid so all marks stay visible.

The offset is deterministic (no RNG) and small: because the base position is
already a ZIP-centroid approximation, nudging marks a fraction of a degree does
not misrepresent the data any more than the geocoding already does. Isolated
points are left exactly where they were.

The geometry is factored into *unit offsets* (``dlat_unit``/``dlon_unit``, the
spiral at ``spread = 1``). Because the offset scales linearly with ``spread``,
callers can either bake a fixed spread (``jitter_overlaps``) or ship the unit
offsets to the browser and scale them live with a Vega slider (see
``charts.overlay`` interactive mode).
"""

import math

import pandas as pd

# Vogel / sunflower spiral: successive points step by the golden angle so a
# stack of any size spreads evenly with no clumping.
_GOLDEN_ANGLE = math.pi * (3 - math.sqrt(5))  # ~2.399963 rad


def jitter_unit_offsets(
    df: pd.DataFrame,
    *,
    lat: str = "Latitude",
    lon: str = "Longitude",
    size: str | None = None,
    precision: int = 4,
) -> pd.DataFrame:
    """Add ``dlat_unit``/``dlon_unit``: per-row spiral offsets at ``spread = 1``.

    Multiply the unit offsets by a spread in degrees to get the actual offset.
    They are ``0`` for isolated points and for the centroid (largest) member of
    each stack. The longitude offset already includes the ``cos(latitude)``
    correction, so a plotted coordinate is ``lon + spread * dlon_unit``.

    Rows whose ``lat``/``lon`` match (rounded to ``precision`` decimals) form a
    stack, ordered largest-first by ``size`` when given so the biggest mark sits
    at the centroid. The returned frame has a fresh ``RangeIndex``.
    """
    out = df.reset_index(drop=True).copy()
    out["dlat_unit"] = 0.0
    out["dlon_unit"] = 0.0

    lat_num = pd.to_numeric(out[lat], errors="coerce")
    lon_num = pd.to_numeric(out[lon], errors="coerce")
    valid = out[lat_num.notna() & lon_num.notna()].copy()
    valid["_klat"] = lat_num[valid.index].round(precision)
    valid["_klon"] = lon_num[valid.index].round(precision)

    for _, members in valid.groupby(["_klat", "_klon"], sort=False):
        n = len(members)
        if n < 2:
            continue
        if size is not None and size in members:
            members = members.sort_values(size, ascending=False, kind="stable")
        centroid_lat = float(lat_num[members.index[0]])
        # Longitude degrees shrink toward the poles; scale so the spiral stays
        # visually round rather than east-west stretched.
        coslat = math.cos(math.radians(centroid_lat)) or 1.0
        for k, row_idx in enumerate(members.index):
            radius = math.sqrt(k / (n - 1))
            theta = k * _GOLDEN_ANGLE
            out.at[row_idx, "dlon_unit"] = (radius * math.cos(theta)) / coslat
            out.at[row_idx, "dlat_unit"] = radius * math.sin(theta)

    return out


def jitter_overlaps(
    df: pd.DataFrame,
    *,
    lat: str = "Latitude",
    lon: str = "Longitude",
    size: str | None = None,
    spread: float = 0.35,
    precision: int = 4,
) -> pd.DataFrame:
    """Add ``lat_jit``/``lon_jit`` columns spreading co-located rows apart.

    A thin wrapper over :func:`jitter_unit_offsets` that bakes a fixed
    ``spread`` (degrees). Singletons and rows with a missing coordinate keep
    their original position. The unit-offset columns are retained so the same
    frame can also drive interactive (slider-scaled) jitter.

    The returned frame has a fresh ``RangeIndex`` (order preserved); callers
    feed it straight to Altair, which ignores the index.
    """
    out = jitter_unit_offsets(df, lat=lat, lon=lon, size=size, precision=precision)
    lat_num = pd.to_numeric(out[lat], errors="coerce")
    lon_num = pd.to_numeric(out[lon], errors="coerce")
    out["lat_jit"] = lat_num + spread * out["dlat_unit"]
    out["lon_jit"] = lon_num + spread * out["dlon_unit"]
    return out
