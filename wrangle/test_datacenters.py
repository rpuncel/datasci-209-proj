"""Tests for owner-name cleanup in the data centers wrangling layer.

Like datasets/test_datasets.py and charts/test_charts.py, these assume the
source data is already cached on disk (a prior `quarto render` or dataset
access warms it).
"""

from wrangle.datacenters import clean_party, enriched_centers


def test_no_unknown_owners():
    centers = enriched_centers()
    unknown = centers[centers["owner_clean"] == "Unknown"]["Name"].tolist()
    assert not unknown, f"Sites with unresolved owner (add to _NAME_OWNER_FALLBACK): {unknown}"


def test_owner_aliases_applied():
    assert clean_party("SpaceXAI #confident") == "xAI"
    assert clean_party("AWS us-east") == "Amazon"
    assert clean_party("Facebook") == "Meta"


def test_new_company_passes_through():
    assert clean_party("Fluidstack #confident") == "Fluidstack"


def test_missing_owner_filled_from_name():
    centers = enriched_centers()
    expected = {
        "DayOne Nusajaya": "DayOne",
        "STACK Infrastructure NVA02": "STACK",
        "Stream Phoenix": "Stream",
        "Vantage TX1": "Vantage",
    }
    for name, owner in expected.items():
        row = centers[centers["Name"] == name]
        assert not row.empty, f"expected site {name!r} in enriched_centers()"
        resolved = row["owner_clean"].iloc[0]
        assert resolved != "Unknown", f"{name} still Unknown"
        assert resolved == owner
