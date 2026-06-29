"""Lazy accessors for WRI's Aqueduct 4.0 water risk dataset.

The archive is large (~260 MB) and not yet consumed by any chart, so it is
fetched only when one of these accessors is first called. The CSV tables live
under a ``CVS/`` subdirectory; the bundled geodatabase is left untouched
(reading it would require geopandas/fiona, which are not project dependencies).
"""

from functools import lru_cache
from pathlib import Path

import pandas as pd

from ._sources import ZipDataset, _DATA_ROOT

# Path of the extracted CSV tables, relative to the extraction directory.
_CSV_DIR = "Aqueduct40_waterrisk_download_Y2023M07D05/CVS"

_SOURCE = ZipDataset(
    url="https://files.wri.org/aqueduct/aqueduct-4-0-water-risk-data.zip",
    dest=_DATA_ROOT / "external" / "aqueduct",
    sentinel=f"{_CSV_DIR}/Aqueduct40_baseline_annual_y2023m07d05.csv",
)


def ensure() -> Path:
    """Download and extract the archive if missing; return the cache dir."""
    return _SOURCE.ensure()


def _read(name: str) -> pd.DataFrame:
    return pd.read_csv(_SOURCE.ensure() / _CSV_DIR / name)


@lru_cache(maxsize=None)
def baseline_annual() -> pd.DataFrame:
    return _read("Aqueduct40_baseline_annual_y2023m07d05.csv")


@lru_cache(maxsize=None)
def baseline_monthly() -> pd.DataFrame:
    return _read("Aqueduct40_baseline_monthly_y2023m07d05.csv")


@lru_cache(maxsize=None)
def future_annual() -> pd.DataFrame:
    return _read("Aqueduct40_future_annual_y2023m07d05.csv")
