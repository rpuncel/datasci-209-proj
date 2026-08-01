"""Reusable Altair chart functions shared by the dashboard, reports, and slides.

Typical .qmd usage::

    import charts
    charts.setup()                      # once, in the first cell
    charts.datacenters.owner_power()    # one-liner per chart cell
"""

from . import datacenters
from . import overlay
from . import money
from . import water
from . import electricity
from . import explorer
from ._theme import interactive, setup

__all__ = [
    "datacenters",
    "overlay",
    "money",
    "water",
    "electricity",
    "explorer",
    "interactive",
    "setup",
]
