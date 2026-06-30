"""Lazy accessors for WRI's Aqueduct 4.0 water risk dataset.

The archive is large (~260 MB) and not yet consumed by any chart, so it is
fetched only when one of these accessors is first called. The CSV tables live
under a ``CVS/`` subdirectory; the bundled geodatabase is left untouched
(reading it would require geopandas/fiona, which are not project dependencies).
"""

from functools import lru_cache
from pathlib import Path

import pandas as pd
import geopandas as gpd

from ._sources import ZipDataset, _DATA_ROOT

# Path of the extracted CSV tables, relative to the extraction directory.
_CSV_DIR = "Aqueduct40_waterrisk_download_Y2023M07D05/CVS"
_GDB_DIR = "Aqueduct40_waterrisk_download_Y2023M07D05/GDB"

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

def _read_gdb(name: str) -> gpd.GeoDataFrame:
    return gpd.read_file(_SOURCE.ensure() / _GDB_DIR / name,
    use_arrow=True,
    layer='baseline_annual',
    where="gid_0='USA'",
    columns=['geomeotry', 'bws_label', 'gid_0']
    )


@lru_cache(maxsize=None)
def baseline_annual() -> pd.DataFrame:
    return _read("Aqueduct40_baseline_annual_y2023m07d05.csv")


@lru_cache(maxsize=None)
def baseline_monthly() -> pd.DataFrame:
    return _read("Aqueduct40_baseline_monthly_y2023m07d05.csv")


@lru_cache(maxsize=None)
def future_annual() -> pd.DataFrame:
    return _read("Aqueduct40_future_annual_y2023m07d05.csv")

def gdb() -> gpd.GeoDataFrame:
    return _read_gdb('Aq40_Y2023D07M05.gdb')