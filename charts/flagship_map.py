"""Flagship interactive map: baseline water stress + owner-linked data centers.

Kept in its own module because it is the dashboard's headline, cross-filtered
view and evolves independently of the plain choropleth builders in
``charts.water``. Clicking a bar or a map point selects that owner and greys out
everything else in both linked views. Needs an interactive renderer
(``charts.interactive``), not the static SVG default.
"""

import altair as alt

from charts import datacenters, overlay, water
from wrangle import datacenters as wd
from wrangle import water as ww
from wrangle.datacenters import POWER
from wrangle.jitter import jitter_overlaps


def baseline_stress_owner_linked() -> alt.HConcatChart:
    """Baseline stress map and site-concentration bars linked by owner selection."""
    owners = sorted(
        set(wd.high_power_low_density()["owner_clean"].dropna())
        | set(ww.us_centers_geocoded()["owner_clean"].dropna())
    )
    owner_scale = alt.Scale(domain=owners, scheme="tableau20")

    brush = alt.selection_point(fields=["owner_clean"])
    condition = alt.when(brush).then(
        alt.Color("owner_clean:N", scale=owner_scale, title="Owner")
    ).otherwise(alt.value("grey"))
    # the map's Owner legend covers both views
    bar_condition = alt.when(brush).then(
        alt.Color("owner_clean:N", scale=owner_scale, legend=None)
    ).otherwise(alt.value("grey"))

    company_bars = datacenters.site_concentration(lines=False).encode(color=bar_condition)

    df = jitter_overlaps(
        ww.us_centers_geocoded().dropna(subset=["Latitude", "Longitude"]),
        size=POWER,
        spread=overlay.JITTER_SPREAD,
        cluster_dist=overlay.CLUSTER_DIST,
    )
    points = overlay.datacenter_points(df, color=condition)

    water_stress = (water.baseline_stress_choropleth() + points).properties(
        width=600,
        height=420,
        title="Baseline Water Stress by US State with Current AI Data Center Locations",
    )

    return (water_stress | company_bars).add_params(brush)
