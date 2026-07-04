"""Reusable Altair chart functions shared by the dashboard, reports, and slides.

Typical .qmd usage::

    import charts
    charts.setup()                      # once, in the first cell
    charts.datacenters.owner_power()    # one-liner per chart cell
"""

from . import datacenters
from . import water
from . import electricity
from ._theme import setup

__all__ = [
    "datacenters",
    "water",
    "electricity",
    "setup",
]
