"""Water-stress frames (WRI Aqueduct 4.0) and data center geocoding."""

from functools import lru_cache
from pathlib import Path

import pandas as pd

import datasets
from constants import STATE_FIPS

from .datacenters import enriched_centers

_DATASETS_DIR = Path(datasets.__file__).parent


@lru_cache(maxsize=None)
def aqueduct_geo():
    """Aqueduct geodatabase polygons dissolved to province (state) level."""
    return datasets.aqueduct.gdb().dissolve(by=["gid_1"])


def _province_stress(csv_name: str) -> pd.DataFrame:
    """U.S. baseline-water-stress scores per state, keyed by FIPS id.

    Uses the ``Tot`` weighting (total gross water withdrawal) of the ``bws``
    indicator from a WRI Aqueduct province-level rankings file.
    """
    frame = pd.read_csv(_DATASETS_DIR / csv_name)
    stress = frame[
        (frame["gid_0"] == "USA")
        & (frame["indicator_name"] == "bws")
        & (frame["weight"] == "Tot")
    ][["name_1", "score", "label", "score_ranked"]].copy()
    stress["id"] = stress["name_1"].map(STATE_FIPS).astype(int)
    return stress


@lru_cache(maxsize=None)
def us_water_stress() -> pd.DataFrame:
    return _province_stress("province_baseline.csv")


@lru_cache(maxsize=None)
def future_us_water_stress() -> pd.DataFrame:
    return _province_stress("province_future.csv")




@lru_cache(maxsize=None)
def future_data_centers() -> pd.DataFrame:
    """Proposed U.S. data centers (FracTracker tracker; not AI-specific)."""
    return pd.read_csv(_DATASETS_DIR / "Data_Centers_Database.csv")
