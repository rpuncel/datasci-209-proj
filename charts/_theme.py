"""Shared Altair configuration for every document that renders project charts."""

import json
import uuid

import altair as alt
from altair.utils.display import compile_with_vegafusion, using_vegafusion
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


# Opt-in interactive embed for charts that need selections. Embeds the chart with
# a native ES-module <script> (`import embed from ".../vega-embed@7/+esm"`). ES
# modules use the browser's own loader, completely independent of RequireJS/AMD,
# so the OJS/RequireJS conflict does not apply and the chart keeps full
# interactivity (tooltips, selections).
def esm_vega_renderer(spec, **metadata):
    # With the vegafusion data transformer, the spec handed to renderers still
    # contains vegafusion+dataset:// placeholders; built-in renderers resolve
    # them via compile_with_vegafusion, so this renderer must too.
    if using_vegafusion():
        spec = compile_with_vegafusion(spec)
    div_id = "vega-" + uuid.uuid4().hex
    spec_json = json.dumps(spec)
    html = (
        f'<div id="{div_id}" class="vega-embed-esm"></div>\n'
        f'<script type="module">\n'
        f'  import embed from "https://cdn.jsdelivr.net/npm/vega-embed@7/+esm";\n'
        f'  embed(document.getElementById("{div_id}"), {spec_json}, {{actions: true}})\n'
        f'    .catch((err) => console.error("vega-embed error:", err));\n'
        f'</script>'
    )
    return {"text/html": html}


def interactive(chart):
    """Render one chart with the browser-side ESM vega-embed instead of the
    static SVG default, keeping selections and tooltips alive."""
    from IPython.display import HTML

    spec = chart.to_dict(context={"pre_transform": False})
    return HTML(esm_vega_renderer(spec)["text/html"])


def setup():
    """Enable the vegafusion transformer and local SVG renderer.

    Call once from the first cell of any .qmd that displays project charts.
    """
    alt.data_transformers.enable("vegafusion")
    alt.data_transformers.disable_max_rows()
    alt.renderers.register("local-svg", svg_renderer)
    alt.renderers.enable("local-svg")
