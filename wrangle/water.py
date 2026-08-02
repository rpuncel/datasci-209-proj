"""Water-stress frames (WRI Aqueduct 4.0) and data center geocoding."""

from functools import lru_cache
from pathlib import Path

import pandas as pd

import datasets
from constants import STATE_FIPS

from .datacenters import CAPEX, H100, POWER, clean_party, enriched_centers, us_centers
from .operator_name import fill_missing_operator_names

_DATASETS_DIR = Path(datasets.__file__).parent

FUTURE_YEARS = (2030, 2050, 2080)
SCENARIOS = {
    "opt": "Optimistic",
    "bau": "Business as usual",
    "pes": "Pessimistic",
}


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
    # Aqueduct uses -9999 as its NoData sentinel (Hawaii in the baseline file).
    stress.loc[stress["score"] < 0, ["score", "score_ranked"]] = pd.NA
    return stress


@lru_cache(maxsize=None)
def us_water_stress() -> pd.DataFrame:
    return _province_stress("province_baseline.csv")


@lru_cache(maxsize=None)
def future_us_water_stress(
    year: int = 2050, scenario: str = "bau"
) -> pd.DataFrame:
    """One unambiguous U.S. future projection per state.

    Aqueduct's future file contains three years crossed with three scenarios.
    Keeping the selector here prevents a many-row lookup from silently choosing
    an arbitrary projection for each state.
    """
    if year not in FUTURE_YEARS:
        raise ValueError(f"year must be one of {FUTURE_YEARS}")
    if scenario not in SCENARIOS:
        raise ValueError(f"scenario must be one of {tuple(SCENARIOS)}")

    frame = pd.read_csv(_DATASETS_DIR / "province_future.csv")
    stress = frame[
        (frame["gid_0"] == "USA")
        & (frame["indicator_name"] == "bws")
        & (frame["weight"] == "Tot")
        & (frame["year"] == year)
        & (frame["scenario"] == scenario)
    ][["name_1", "score", "label", "score_ranked"]].copy()
    stress["id"] = stress["name_1"].map(STATE_FIPS).astype(int)
    return stress


@lru_cache(maxsize=None)
def water_stress_comparison() -> pd.DataFrame:
    """Baseline and all nine future projections with change from baseline."""
    baseline = us_water_stress().rename(
        columns={
            "score": "baseline_score",
            "label": "baseline_label",
            "score_ranked": "baseline_score_ranked",
        }
    )
    frames = []
    for year in FUTURE_YEARS:
        for scenario, scenario_label in SCENARIOS.items():
            future = future_us_water_stress(year, scenario).rename(
                columns={
                    "score": "future_score",
                    "label": "future_label",
                    "score_ranked": "future_score_ranked",
                }
            )
            comparison = baseline.merge(
                future,
                on=["id", "name_1"],
                how="outer",
                validate="one_to_one",
            )
            comparison["year"] = year
            comparison["scenario"] = scenario
            comparison["scenario_label"] = scenario_label
            comparison["delta"] = (
                comparison["future_score"] - comparison["baseline_score"]
            )
            frames.append(comparison)

    return pd.concat(frames, ignore_index=True)


@lru_cache(maxsize=None)
def water_stress_wide() -> pd.DataFrame:
    """One row per state with all projections in uniquely named columns.

    Vega-Lite lookups require the lookup key to be unique. Keeping the nine
    projections in columns lets browser-side parameters choose a projection
    after a single, reliable state lookup.
    """
    baseline = us_water_stress()[
        ["id", "name_1", "score", "label"]
    ].rename(columns={"score": "baseline_score", "label": "baseline_label"})

    result = baseline
    for year in FUTURE_YEARS:
        for scenario in SCENARIOS:
            suffix = f"{year}_{scenario}"
            future = future_us_water_stress(year, scenario)[
                ["id", "name_1", "score", "label"]
            ].rename(
                columns={
                    "score": f"future_score_{suffix}",
                    "label": f"future_label_{suffix}",
                }
            )
            result = result.merge(
                future,
                on=["id", "name_1"],
                how="outer",
                validate="one_to_one",
            )
            result[f"delta_{suffix}"] = (
                result[f"future_score_{suffix}"] - result["baseline_score"]
            )

    return result




@lru_cache(maxsize=None)
def future_data_centers() -> pd.DataFrame:
    """Proposed U.S. data centers (FracTracker tracker; not AI-specific).

    ``operator_name`` arrives blank on ~45% of rows; ``fill_missing_operator_names``
    backfills what it can (see ``wrangle.operator_name`` for the inference
    tiers) and tags every row's ``operator_name_source`` as "original",
    "inferred", or "missing" so downstream consumers can tell real FracTracker
    data apart from an inferred guess if that distinction ever matters.
    """
    raw = pd.read_csv(_DATASETS_DIR / "Data_Centers_Database.csv")
    return fill_missing_operator_names(raw)


@lru_cache(maxsize=None)
def explorer_sites() -> pd.DataFrame:
    """Current AI sites and proposed projects in the unified explorer's schema.

    One row per site, feeding all three maps *and* the shared owner bars in
    ``charts.explorer``. Two things differ from ``comparison_sites()``:

    - the owner column is named ``owner_clean``, matching the canonical name
      used everywhere else in the project (and by ``owner_colors``), so one
      palette and one selection cover every view;
    - the capital / compute / rank columns from the enriched Epoch frame ride
      along for the money and electricity map tooltips. They are NaN on the
      proposed rows, which is why every map sizes its marks by ``capacity_mw``:
      a capex-sized mark would simply not render for a proposed site.

    ``latitude`` / ``longitude`` are lowercase and load-bearing: the shared
    geographic brush stores its extents against the field names bound to the
    lat/lon channels, and the owner bars' ``transform_filter(geo_brush)`` tests
    those same names.
    """
    current = us_centers()
    current_sites = pd.DataFrame(
        {
            "site_id": "current-" + current.index.astype(str),
            "site_name": current["Name"],
            "address": current["Address"],
            "owner_clean": current["owner_clean"],
            "capacity_mw": pd.to_numeric(current[POWER], errors="coerce"),
            "capex_b": pd.to_numeric(current[CAPEX], errors="coerce"),
            "h100_eq": pd.to_numeric(current[H100], errors="coerce"),
            "rank": current["rank"],
            "latitude": current["Latitude"],
            "longitude": current["Longitude"],
            "site_period": "Baseline",
            "site_type": "Current AI site",
        }
    )

    proposed = (
        future_data_centers()
        .query("status == 'Proposed'")
        .dropna(subset=["lat", "long"])
        .reset_index(drop=True)
    )
    proposed_sites = pd.DataFrame(
        {
            "site_id": "proposed-" + proposed.index.astype(str),
            "site_name": proposed["facility_name"],
            "address": proposed["address"],
            # FracTracker operator strings are free text ("Meta Platforms,
            # Inc."); clean_party collapses them onto the same canonical labels
            # the Epoch rows already use, so one owner keeps one color and one
            # bar across both site layers.
            "owner_clean": proposed["operator_name"].map(clean_party).fillna("Unknown"),
            "capacity_mw": pd.to_numeric(proposed["mw"], errors="coerce"),
            "capex_b": pd.NA,
            "h100_eq": pd.NA,
            "rank": pd.NA,
            "latitude": proposed["lat"],
            "longitude": proposed["long"],
            "site_period": "Future",
            "site_type": "Proposed project",
        }
    )

    sites = pd.concat([current_sites, proposed_sites], ignore_index=True)
    sites["capacity_mw"] = sites["capacity_mw"].fillna(0)
    for column in ("capex_b", "h100_eq", "rank"):
        sites[column] = pd.to_numeric(sites[column], errors="coerce")
    return sites


@lru_cache(maxsize=None)
def comparison_sites() -> pd.DataFrame:
    """Current AI sites and proposed projects in one plotting schema."""
    centers = enriched_centers()
    current = (
        centers[centers["Country"] == "United States"]
        .dropna(subset=["Latitude", "Longitude"])
        .reset_index(drop=True)
    )
    current_sites = pd.DataFrame(
        {
            "site_id": "current-" + current.index.astype(str),
            "site_name": current["Name"],
            "address": current["Address"],
            "operator": current["owner_clean"],
            "capacity_mw": pd.to_numeric(current["Current power (MW)"], errors="coerce"),
            "latitude": current["Latitude"],
            "longitude": current["Longitude"],
            "site_period": "Baseline",
            "site_type": "Current AI site",
        }
    )

    proposed = (
        future_data_centers()
        .query("status == 'Proposed'")
        .dropna(subset=["lat", "long"])
        .reset_index(drop=True)
    )
    proposed_sites = pd.DataFrame(
        {
            "site_id": "proposed-" + proposed.index.astype(str),
            "site_name": proposed["facility_name"],
            "address": proposed["address"],
            "operator": proposed["operator_name"].fillna("Unknown"),
            "capacity_mw": pd.to_numeric(proposed["mw"], errors="coerce"),
            "latitude": proposed["lat"],
            "longitude": proposed["long"],
            "site_period": "Future",
            "site_type": "Proposed project",
        }
    )
    sites = pd.concat([current_sites, proposed_sites], ignore_index=True)
    sites["capacity_mw"] = sites["capacity_mw"].fillna(0)
    return sites
