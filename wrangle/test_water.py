"""Validation tests for the interactive water-stress comparison."""

import pandas as pd
import pytest

from wrangle import water


def test_future_selector_returns_one_row_per_state():
    for year in water.FUTURE_YEARS:
        for scenario in water.SCENARIOS:
            frame = water.future_us_water_stress(year, scenario)
            assert len(frame) == 50
            assert frame["id"].is_unique


def test_future_selector_rejects_unknown_options():
    with pytest.raises(ValueError):
        water.future_us_water_stress(2040, "bau")
    with pytest.raises(ValueError):
        water.future_us_water_stress(2050, "unknown")


def test_comparison_has_all_nine_projections_and_valid_deltas():
    frame = water.water_stress_comparison()

    assert set(frame["year"]) == set(water.FUTURE_YEARS)
    assert set(frame["scenario"]) == set(water.SCENARIOS)
    assert not frame.duplicated(["id", "year", "scenario"]).any()

    comparable = frame.dropna(subset=["baseline_score", "future_score"])
    expected = comparable["future_score"] - comparable["baseline_score"]
    pd.testing.assert_series_equal(
        comparable["delta"].reset_index(drop=True),
        expected.reset_index(drop=True),
        check_names=False,
    )


def test_aqueduct_nodata_sentinel_is_missing():
    hawaii = water.us_water_stress().query("name_1 == 'Hawaii'").iloc[0]
    assert pd.isna(hawaii["score"])


def test_wide_comparison_has_one_lookup_row_per_state():
    frame = water.water_stress_wide()
    assert frame["id"].is_unique
    assert len(frame) == 51
    assert "future_score_2050_bau" in frame
    assert "delta_2080_pes" in frame


def test_site_comparison_switches_between_current_and_proposed():
    sites = water.comparison_sites()
    assert set(sites["site_period"]) == {"Baseline", "Future"}
    assert set(sites["site_type"]) == {"Current AI site", "Proposed project"}
    assert sites["site_id"].is_unique


def test_explorer_sites_schema():
    sites = water.explorer_sites()

    expected = {
        "site_id", "site_name", "address", "owner_clean", "capacity_mw",
        "capex_b", "h100_eq", "rank", "latitude", "longitude",
        "site_period", "site_type",
    }
    assert expected <= set(sites.columns)
    assert sites["site_id"].is_unique
    assert set(sites["site_period"]) == {"Baseline", "Future"}
    assert set(sites["site_type"]) == {"Current AI site", "Proposed project"}


def test_explorer_sites_have_plottable_coordinates():
    """A null coordinate silently drops a site from every map and from the
    brushed owner ranking, so it must never reach the spec."""
    sites = water.explorer_sites()
    assert not sites["latitude"].isna().any()
    assert not sites["longitude"].isna().any()
    assert not sites["capacity_mw"].isna().any()


def test_explorer_sites_carry_enrichment_only_on_baseline_rows():
    """The Epoch capital/compute columns exist for current sites only; the
    maps rely on that (they size by capacity_mw, not capex, so proposed rows
    still render)."""
    sites = water.explorer_sites()
    baseline = sites[sites["site_period"] == "Baseline"]
    future = sites[sites["site_period"] == "Future"]

    assert baseline["capex_b"].notna().any()
    assert baseline["h100_eq"].notna().any()
    assert future["capex_b"].isna().all()
    assert future["h100_eq"].isna().all()


def test_explorer_sites_canonicalize_owner_across_both_layers():
    """Owner labels must collapse onto the same canonical names in both
    layers, otherwise a company splits into two bars and two colors."""
    sites = water.explorer_sites()

    assert "owner_clean" in sites
    assert not sites["owner_clean"].isna().any()

    future_owners = set(sites.query("site_period == 'Future'")["owner_clean"])
    baseline_owners = set(sites.query("site_period == 'Baseline'")["owner_clean"])
    # The FracTracker operator strings are free text; clean_party should map at
    # least the big builders onto labels the Epoch rows already use.
    assert future_owners & baseline_owners
