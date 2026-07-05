"""Shared Altair configuration for every document that renders project charts."""

import altair as alt
from altair.utils.mimebundle import spec_to_mimebundle


# Some pages mix Altair (Vega) charts with Observable JS (OJS) cells. Adding OJS
# makes Quarto load RequireJS, which sends Altair's default HTML renderer down its
# AMD branch, where "vega-embed" no longer resolves to the callable embed function
# -> "vegaEmbed is not a function" and every chart fails to render.
#
# Fix: render each chart to SVG at build time with vl-convert-python. The SVG is
# embedded directly in the Quarto output, so charts do not depend on browser-side
# Vega scripts or external CDNs. This is static output, not interactive Vega.
def svg_renderer(spec, **metadata):
    bundle = spec_to_mimebundle(spec, format="svg", mode="vega-lite", **metadata)
    return {"text/html": f'<div class="altair-svg-chart">{bundle["image/svg+xml"]}</div>'}


def setup():
    """Enable the vegafusion transformer and local SVG renderer.

    Call once from the first cell of any .qmd that displays project charts.
    """
    alt.data_transformers.enable("vegafusion")
    alt.data_transformers.disable_max_rows()
    alt.renderers.register("local-svg", svg_renderer)
    alt.renderers.enable("local-svg")
