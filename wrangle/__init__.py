"""Derived, analysis-ready frames built on top of the raw ``datasets`` loaders.

Everything here is a lazy, memoized zero-arg function so importing is cheap
and repeated calls across .qmd cells share one computation.
"""

from . import datacenters
from . import water

__all__ = [
    "datacenters",
    "water",
]
