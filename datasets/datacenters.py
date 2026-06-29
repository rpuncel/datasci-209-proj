"""Lazy accessors for Epoch AI's frontier data center dataset."""

from functools import lru_cache

import pandas as pd

from ._sources import ZipDataset, _DATA_ROOT

_SOURCE = ZipDataset(
    url="https://epoch.ai/data/data_centers/data_centers.zip",
    dest=_DATA_ROOT / "external" / "data_centers",
    sentinel="data_centers.csv",
)


def _read(name: str) -> pd.DataFrame:
    return pd.read_csv(_SOURCE.ensure() / name)


@lru_cache(maxsize=None)
def data_centers() -> pd.DataFrame:
    return _read("data_centers.csv")


@lru_cache(maxsize=None)
def data_center_chillers() -> pd.DataFrame:
    return _read("data_center_chillers.csv")


@lru_cache(maxsize=None)
def data_center_cooling_towers() -> pd.DataFrame:
    return _read("data_center_cooling_towers.csv")


@lru_cache(maxsize=None)
def data_center_timelines() -> pd.DataFrame:
    return _read("data_center_timelines.csv")


@lru_cache(maxsize=None)
def data_center_chip_quantities() -> pd.DataFrame:
    return _read("data_center_chip_quantities.csv")
