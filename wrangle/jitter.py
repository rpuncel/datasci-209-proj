"""Deterministic jitter for overlapping map marks.

U.S. data centers are placed at ZIP-code centroids (see ``wrangle.water``), so
sites sharing a ZIP land on the *exact same* coordinate and their marks stack
perfectly. Sites in neighbouring ZIPs land close together and — because the
marks are sized by power/capex and can be large — visually overlap too. This
module groups nearby marks into a cluster and spreads each cluster onto a small
golden-angle spiral so all marks stay visible.

Clustering is by proximity (single linkage within ``cluster_dist`` degrees), not
exact coordinate match, so metro clusters (e.g. Ashburn, San Antonio, Columbus)
separate as well as exact ZIP collisions. ``cluster_dist = 0`` recovers
exact-match grouping.

Within a cluster the largest mark stays anchored at its true position (offset
0) and the rest fan out around their own positions, so nothing is collapsed to
a shared centroid. The offset is deterministic (no RNG) and small: the base
position is already a ZIP-centroid approximation, so nudging marks a fraction of
a degree does not misrepresent the data any more than the geocoding already
does. Isolated points are left exactly where they were.

The geometry is factored into *unit offsets* (``dlat_unit``/``dlon_unit``, the
spiral at ``spread = 1``). Because the offset scales linearly with ``spread``,
callers can either bake a fixed spread (``jitter_overlaps``) or ship the unit
offsets to the browser and scale them live with a Vega slider (see
``charts.overlay`` interactive mode).
"""

import math

import pandas as pd

# Vogel / sunflower spiral: successive points step by the golden angle so a
# cluster of any size spreads evenly with no clumping.
_GOLDEN_ANGLE = math.pi * (3 - math.sqrt(5))  # ~2.399963 rad


def _proximity_clusters(lat: dict, lon: dict, cluster_dist: float) -> list[list]:
    """Single-linkage clusters of labels within ``cluster_dist`` degrees.

    ``lat``/``lon`` map row label -> coordinate. Distance uses a ``cos(lat)``
    correction so the threshold is roughly isotropic on the ground.
    """
    labels = list(lat)
    parent = {label: label for label in labels}

    def find(a):
        root = a
        while parent[root] != root:
            root = parent[root]
        while parent[a] != root:  # path compression
            parent[a], a = root, parent[a]
        return root

    for i, li in enumerate(labels):
        for lj in labels[i + 1 :]:
            dlat = lat[li] - lat[lj]
            dlon = (lon[li] - lon[lj]) * math.cos(math.radians((lat[li] + lat[lj]) / 2))
            if math.hypot(dlat, dlon) <= cluster_dist:
                ri, rj = find(li), find(lj)
                if ri != rj:
                    parent[ri] = rj

    clusters: dict = {}
    for label in labels:
        clusters.setdefault(find(label), []).append(label)
    return list(clusters.values())


def jitter_unit_offsets(
    df: pd.DataFrame,
    *,
    lat: str = "Latitude",
    lon: str = "Longitude",
    size: str | None = None,
    cluster_dist: float = 0.0,
) -> pd.DataFrame:
    """Add ``dlat_unit``/``dlon_unit``: per-row spiral offsets at ``spread = 1``.

    Multiply the unit offsets by a spread in degrees to get the actual offset.
    They are ``0`` for isolated points and for the largest member of each
    cluster. The longitude offset already includes the ``cos(latitude)``
    correction, so a plotted coordinate is ``lon + spread * dlon_unit``.

    Rows within ``cluster_dist`` degrees of each other (single linkage) form a
    cluster, ordered largest-first by ``size`` when given so the biggest mark
    keeps its true position and smaller marks fan out. ``cluster_dist = 0``
    groups only exact-coincident points. The returned frame has a fresh
    ``RangeIndex``.
    """
    out = df.reset_index(drop=True).copy()
    out["dlat_unit"] = 0.0
    out["dlon_unit"] = 0.0

    lat_num = pd.to_numeric(out[lat], errors="coerce")
    lon_num = pd.to_numeric(out[lon], errors="coerce")
    valid = out.index[lat_num.notna() & lon_num.notna()]
    lat_map = {label: float(lat_num[label]) for label in valid}
    lon_map = {label: float(lon_num[label]) for label in valid}

    for members in _proximity_clusters(lat_map, lon_map, cluster_dist):
        n = len(members)
        if n < 2:
            continue
        if size is not None and size in out.columns:
            members = sorted(
                members,
                key=lambda label: out.at[label, size]
                if pd.notna(out.at[label, size])
                else float("-inf"),
                reverse=True,  # largest first -> anchored at radius 0
            )
        # Longitude degrees shrink toward the poles; scale so the spiral stays
        # visually round rather than east-west stretched.
        coslat = math.cos(math.radians(lat_map[members[0]])) or 1.0
        for k, label in enumerate(members):
            radius = math.sqrt(k / (n - 1))
            theta = k * _GOLDEN_ANGLE
            out.at[label, "dlon_unit"] = (radius * math.cos(theta)) / coslat
            out.at[label, "dlat_unit"] = radius * math.sin(theta)

    return out


def jitter_overlaps(
    df: pd.DataFrame,
    *,
    lat: str = "Latitude",
    lon: str = "Longitude",
    size: str | None = None,
    spread: float = 0.35,
    cluster_dist: float = 0.0,
) -> pd.DataFrame:
    """Add ``lat_jit``/``lon_jit`` columns spreading overlapping rows apart.

    A thin wrapper over :func:`jitter_unit_offsets` that bakes a fixed
    ``spread`` (degrees). Singletons and rows with a missing coordinate keep
    their original position. The unit-offset columns are retained so the same
    frame can also drive interactive (slider-scaled) jitter.

    The returned frame has a fresh ``RangeIndex`` (order preserved); callers
    feed it straight to Altair, which ignores the index.
    """
    out = jitter_unit_offsets(
        df, lat=lat, lon=lon, size=size, cluster_dist=cluster_dist
    )
    lat_num = pd.to_numeric(out[lat], errors="coerce")
    lon_num = pd.to_numeric(out[lon], errors="coerce")
    out["lat_jit"] = lat_num + spread * out["dlat_unit"]
    out["lon_jit"] = lon_num + spread * out["dlon_unit"]
    return out
