"""Smoke tests: every public chart function builds a valid Vega-Lite spec.

Like datasets/test_datasets.py, these assume the source data is already
cached on disk (a prior `quarto render` or dataset access warms it).
"""

import altair as alt
import pytest

from charts import datacenters as dc_charts
from charts import water as water_charts

CHART_FUNCS = [
    dc_charts.cost_vs_energy,
    dc_charts.state_power,
    dc_charts.owner_power,
    dc_charts.site_concentration,
    dc_charts.power_vs_capital_cost,
    dc_charts.timeline_with_milestones,
    dc_charts.annual_additions,
    dc_charts.capital_pipeline,
    dc_charts.power_vs_compute_density,
    dc_charts.higher_power_lower_density_sites,
    dc_charts.continental_comparison,
    dc_charts.us_state_concentration,
    water_charts.water_stress_geo_map,
    water_charts.baseline_stress_choropleth,
    water_charts.baseline_stress_with_datacenters,
    water_charts.future_stress_choropleth,
    water_charts.future_stress_with_datacenters,
    water_charts.stress_comparison,
]


@pytest.fixture(autouse=True)
def plain_data_transformer():
    """Validate specs with inline data; renderer-specific setup is exercised
    by the actual Quarto render, not here."""
    with alt.data_transformers.enable("default", max_rows=None):
        yield


@pytest.mark.parametrize("chart_func", CHART_FUNCS, ids=lambda f: f.__name__)
def test_chart_builds_valid_spec(chart_func):
    chart = chart_func()
    assert isinstance(chart, alt.TopLevelMixin)
    spec = chart.to_dict()
    assert "$schema" in spec
