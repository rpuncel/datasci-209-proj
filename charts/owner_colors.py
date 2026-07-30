"""Stable, choropleth-safe owner → color mapping for all project charts.

Water-stress maps use Vega ``reds``, so company marks that overlay those maps
need colors that stay distinct from the fill (no reds / pinks / orange-reds).
Every chart that encodes owner/operator as color should use ``owner_scale`` /
``owner_color`` so the same company keeps the same hue across views.
"""

from __future__ import annotations

import hashlib
from functools import lru_cache
from typing import Iterable

import altair as alt

# Pinned colors for canonical AI-owner labels (owner_clean). Chosen to contrast
# against light→dark red choropleths and against each other.
OWNER_COLORS: dict[str, str] = {
    "Amazon": "#1D4E89",
    "Microsoft": "#0F7B6C",
    "Google": "#2E86AB",
    "Meta": "#6C3483",
    "Oracle": "#1A5276",
    "xAI": "#8E44AD",
    "CoreWeave": "#117A65",
    "QTS": "#B7950B",
    "Huawei": "#1B4F72",
    "DayOne": "#148F77",
    "Alibaba": "#5D6D7E",
    "Vantage": "#2874A6",
    "STACK": "#16A085",
    "Stream": "#7D3C98",
    "Softbank": "#1E8449",
    "Fluidstack": "#2980B9",
    "Nscale": "#884EA0",
    "Firmus": "#0E6655",
    "G42": "#2471A3",
    "VNET": "#5B7083",
    "Unknown": "#94A3B8",
}

# Fallback cycle for proposed-project operators and any new owner labels.
# Same constraint: no reds that disappear into the water-stress fill.
_FALLBACK_PALETTE: tuple[str, ...] = (
    "#0B3D91",
    "#1A7A4C",
    "#5B2C6F",
    "#0E7C7B",
    "#A67C00",
    "#1F4E79",
    "#2A9D8F",
    "#6A4C93",
    "#14746F",
    "#3D348B",
    "#05668D",
    "#028090",
    "#7B2D8E",
    "#264653",
    "#457B9D",
    "#1D3557",
    "#6D597A",
    "#2C6E49",
    "#3A506B",
    "#5C4D7A",
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
