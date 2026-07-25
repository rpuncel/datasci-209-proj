"""Deterministic jitter for co-located map marks.

U.S. data centers are placed at ZIP-code centroids (see ``wrangle.water``), so
every site sharing a ZIP lands on the *exact same* coordinate and its mark
stacks perfectly on its neighbors. This module spreads each such stack onto a
small golden-angle spiral around its shared centroid so all marks stay visible.

The offset is deterministic (no RNG) and small: because the base position is
already a ZIP-centroid approximation, nudging marks a fraction of a degree does
not misrepresent the data any more than the geocoding already does. Isolated
points are left exactly where they were.
"""

import math

import pandas as pd

# Vogel / sunflower spiral: successive points step by the golden angle so a
# stack of any size spreads evenly with no clumping.
_GOLDEN_ANGLE = math.pi * (3 - math.sqrt(5))  # ~2.399963 rad


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

    Rows whose ``lat``/``lon`` match (rounded to ``precision`` decimals) are
    treated as a stack and distributed on a golden-angle spiral of radius up to
    ``spread`` degrees around their shared centroid. Singletons and rows with a
    missing coordinate keep their original position.

    Parameters
    ----------
    lat, lon : source coordinate columns.
    size : optional column used to order a stack largest-first, so the biggest
        mark sits at the centroid (radius 0) and smaller marks spiral outward.
    spread : maximum radial offset in degrees for the outermost mark. Small by
        design; eye-tune in preview.
    precision : decimals to round coordinates to when grouping a stack.

    The returned frame has a fresh ``RangeIndex`` (order preserved); callers
    feed it straight to Altair, which ignores the index.
    """
    out = df.reset_index(drop=True).copy()
    out["lat_jit"] = pd.to_numeric(out[lat], errors="coerce")
    out["lon_jit"] = pd.to_numeric(out[lon], errors="coerce")

    valid = out[out["lat_jit"].notna() & out["lon_jit"].notna()].copy()
    valid["_klat"] = valid["lat_jit"].round(precision)
    valid["_klon"] = valid["lon_jit"].round(precision)

    for _, members in valid.groupby(["_klat", "_klon"], sort=False):
        n = len(members)
        if n < 2:
            continue
        if size is not None and size in members:
            members = members.sort_values(size, ascending=False, kind="stable")
        centroid_lat = float(members["lat_jit"].iloc[0])
        # Longitude degrees shrink toward the poles; scale so the spiral stays
        # visually round rather than east-west stretched.
        coslat = math.cos(math.radians(centroid_lat)) or 1.0
        for k, row_idx in enumerate(members.index):
            radius = spread * math.sqrt(k / (n - 1))
            theta = k * _GOLDEN_ANGLE
            out.at[row_idx, "lon_jit"] += (radius * math.cos(theta)) / coslat
            out.at[row_idx, "lat_jit"] += radius * math.sin(theta)

    return out
