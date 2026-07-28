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
