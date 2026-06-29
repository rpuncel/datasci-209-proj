"""Lazy, cached data loaders for the project's source datasets.

Importing this package is cheap and triggers no network access. Each accessor
downloads + extracts its archive on first call only if the data is not already
cached on disk, then memoizes the parsed DataFrame.
"""

from . import aqueduct
from .datacenters import (
    data_center_chillers,
    data_center_chip_quantities,
    data_center_cooling_towers,
    data_center_timelines,
    data_centers,
)

__all__ = [
    "data_centers",
    "data_center_chillers",
    "data_center_cooling_towers",
    "data_center_timelines",
    "data_center_chip_quantities",
    "aqueduct",
]
