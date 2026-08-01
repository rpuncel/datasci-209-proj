"""Stable, choropleth-safe owner → color mapping for all project charts.

Water-stress maps use Vega ``reds``, so company marks that overlay those maps
need colors that stay distinct from the fill (avoid deep reds / pinks).
Every chart that encodes owner/operator as color should use ``owner_scale`` /
``owner_color`` so the same company keeps the same hue across views.
"""

from __future__ import annotations

import hashlib
from functools import lru_cache
from typing import Iterable

import altair as alt

# Tableau-inspired categorical colors with reds removed so overlays stay
# readable on water-stress choropleths. High chroma so the top owners separate
# clearly in legends and small marks.
OWNER_COLORS: dict[str, str] = {
    "Amazon": "#4E79A7",      # blue
    "Microsoft": "#F28E2B",   # orange
    "Google": "#59A14F",      # green
    "Meta": "#B07AA1",        # purple
    "xAI": "#EDC948",         # yellow
    "CoreWeave": "#76B7B2",   # teal
    "Oracle": "#9C755F",      # brown
    "QTS": "#FF9D57",         # light orange
    "Huawei": "#8CD17D",      # light green
    "DayOne": "#499894",      # dark teal
    "Alibaba": "#D7B5A6",     # tan
    "Vantage": "#A0CBE8",     # light blue
    "STACK": "#8A6DCE",       # violet
    "Stream": "#FFBE7D",      # peach
    "Softbank": "#86BCB6",    # seafoam
    "Fluidstack": "#6B9AC4",  # medium blue
    "Nscale": "#D4A6C8",      # lilac
    "Firmus": "#B6992D",      # olive
    "G42": "#3A7D44",         # forest
    "VNET": "#BAB0AC",        # warm gray
    "Unknown": "#9CA3AF",
}

# Fallback cycle for proposed-project operators and any new owner labels.
_FALLBACK_PALETTE: tuple[str, ...] = (
    "#4E79A7",
    "#F28E2B",
    "#59A14F",
    "#B07AA1",
    "#EDC948",
    "#76B7B2",
    "#9C755F",
    "#FF9D57",
    "#8CD17D",
    "#499894",
    "#A0CBE8",
    "#8A6DCE",
    "#FFBE7D",
    "#86BCB6",
    "#6B9AC4",
    "#D4A6C8",
    "#B6992D",
    "#3A7D44",
    "#D7B5A6",
    "#5B6E8C",
)

_KNOWN_BY_LENGTH = sorted(
    (name for name in OWNER_COLORS if name != "Unknown"),
    key=len,
    reverse=True,
)


def resolve_owner_key(name: str) -> str | None:
    """Map a free-text operator label onto a pinned owner when possible."""
    text = str(name).strip()
    if not text:
        return None
    if text in OWNER_COLORS:
        return text
    lower = text.lower()
    for known in _KNOWN_BY_LENGTH:
        if known.lower() in lower:
            return known
    return None


def color_for(name: str) -> str:
    """Return the stable hex color for an owner / operator label."""
    key = resolve_owner_key(name)
    if key is not None:
        return OWNER_COLORS[key]
    digest = hashlib.md5(str(name).strip().encode("utf-8")).hexdigest()
    return _FALLBACK_PALETTE[int(digest, 16) % len(_FALLBACK_PALETTE)]


@lru_cache(maxsize=None)
def canonical_owners() -> tuple[str, ...]:
    """Canonical owner_clean labels from the Epoch AI centers table."""
    from wrangle import datacenters as dc

    return tuple(sorted(dc.enriched_centers()["owner_clean"].dropna().unique()))


def owner_domain(extra: Iterable[str] | None = None) -> list[str]:
    """Sorted domain: all canonical owners plus any extras from a chart."""
    names = set(canonical_owners())
    if extra is not None:
        names.update(str(v).strip() for v in extra if v is not None and str(v).strip())
    return sorted(names)


def owner_scale(extra: Iterable[str] | None = None) -> alt.Scale:
    """Altair scale with a fixed owner→color assignment."""
    domain = owner_domain(extra)
    return alt.Scale(domain=domain, range=[color_for(name) for name in domain])


def owner_color(
    field: str = "owner_clean",
    *,
    title: str | None = "Owner",
    legend=alt.Undefined,
    extra: Iterable[str] | None = None,
    **kwargs,
) -> alt.Color:
    """``alt.Color`` encoding using the shared owner palette."""
    return alt.Color(
        f"{field}:N",
        title=title,
        scale=owner_scale(extra),
        legend=legend,
        **kwargs,
    )
