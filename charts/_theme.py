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


# A fixed pixel width baked into the spec can only ever be right for one
# screen. Vega-Lite's own "container" autosize collapses to a small fixed
# default once a view sits inside an hconcat/vconcat (confirmed on the money
# charts in index.qmd), so it can't rescale a multi-map concat like this one.
#
# CSS-transform-scaling the rendered SVG was tried and rejected: it visually
# resizes the chart, but Vega's pixel-to-data mapping for interval selections
# on a projected geo brush does not correctly invert an ancestor CSS
# transform (confirmed empirically: a drag landed with the brush rectangle's
# y-extent off by hundreds of pixels, sometimes rendering off-canvas).
#
# Instead, re-derive the actual Vega-Lite spec at the target width: walk the
# JSON and multiply every `width`/`height` key by the container/natural-width
# ratio, then re-embed. Vega then computes its own scales and hit-testing
# natively at that size, so pointer interactions are exact at any width. This
# re-embeds (and drops any live selection) on each resize, which is an
# acceptable cost for a rare event; legend/axis pixel constants (minExtent,
# gradientLength, symbolSize, labelLimit) are untouched, so they don't scale
# with the marks -- a cosmetic tradeoff, not a correctness one.
_RESPONSIVE_RENDER_JS = """
const rescale = (node, factor) => {
  if (Array.isArray(node)) return node.map((n) => rescale(n, factor));
  if (node && typeof node === "object") {
    const out = {};
    for (const [k, v] of Object.entries(node)) {
      out[k] = (k === "width" || k === "height") && typeof v === "number"
        ? v * factor
        : rescale(v, factor);
    }
    return out;
  }
  return node;
};
"""

# alt.binding_range has no notion of custom tick labels -- the browser <input
# type="range"> just carries the raw 0-3 value, and vega-embed's own <output>
# echoes that number back verbatim. Rather than fight the binding for
# labeled positions, let it render normally and relabel it after the fact:
# hide the numeric output (styles.css) and drive a text span off the same
# input's `input` event instead. Re-run after every embed, not just once --
# `renderAt` finalizes and recreates the view (and its bind form) on each
# resize, so the input this attaches to does not survive a rescale.
_WATER_STEP_LABELS_JS = """
const enhanceWaterStepControl = () => {
  const container = document.getElementById("water-time-control");
  if (!container) return;
  const input = container.querySelector('input[type="range"]');
  if (!input) return;
  // Vega's own raw-value echo, appended as the input's next sibling. When
  // bind targets a custom `element` (as here) this isn't wrapped in the
  // `.vega-bind-range` div vega-embed's default form uses, so the CSS rule
  // hiding `output` there doesn't reach it -- hide it directly instead,
  // captured before we insert our own label so we grab the right node.
  const echo = input.nextElementSibling;
  if (echo) echo.style.display = "none";

  const label = document.createElement("span");
  label.className = "water-step-label";
  input.insertAdjacentElement("afterend", label);

  const stepLabels = ["Current", "2030", "2050", "2080"];
  const update = () => {
    label.textContent = stepLabels[Number(input.value)] ?? input.value;
  };
  input.addEventListener("input", update);
  update();
};
"""

def _render_at_js(responsive: bool) -> str:
    rescale_call = "factor === 1 ? baseSpec : rescale(baseSpec, factor)"
    fit_block = """
    // Measure the wrapper div (display: block, sized by the dashboard card),
    // not the chart-view div itself: that one is `display: inline-block` (see
    // styles.css), which shrink-wraps to its own content -- so its clientWidth
    // would just mirror back whatever we last rendered, a self-referential
    // measurement that drifts on every pass instead of settling.
    const measureEl = document.getElementById(divId);
    let lastWidth = null;
    let resizeTimer = null;
    const fitToContainer = async () => {
      const available = measureEl.clientWidth;
      if (!available || available === lastWidth) return;
      lastWidth = available;
      // width/height keys scale linearly with `factor`, but legend/axis pixel
      // constants (minExtent, gradientLength, spacing, padding) don't, so
      // rendered width is an affine function of factor, not a proportional
      // one -- a single `available / naturalWidth` estimate overshoots by
      // however much of the render is that fixed overhead. Refine by
      // measuring the actual result and correcting, converging in a couple
      // of passes regardless of how big that fixed portion turns out to be.
      let factor = available / naturalWidth;
      for (let i = 0; i < 4; i++) {
        const actual = await renderAt(factor);
        const error = available - actual;
        if (Math.abs(error) < 2) break;
        factor *= available / actual;
      }
    };
    new ResizeObserver(() => {
      clearTimeout(resizeTimer);
      resizeTimer = setTimeout(
        () => fitToContainer().catch((err) => console.error("vega-embed error:", err)),
        150
      );
    }).observe(measureEl);
    """ if responsive else ""
    return f"""
{_WATER_STEP_LABELS_JS}
let currentView = null;
let naturalWidth = null;

const renderAt = async (factor) => {{
  if (currentView) currentView.finalize();
  const spec = {rescale_call};
  const result = await embed(document.getElementById(viewId), spec, {{
    actions: true, renderer: "svg", bind: document.getElementById(controlsId),
  }});
  currentView = result.view;
  enhanceWaterStepControl();
  const renderedWidth = document.getElementById(viewId)
    .querySelector("svg").width.baseVal.value;
  if (naturalWidth === null) {{
    naturalWidth = renderedWidth;
  }}
  return renderedWidth;
}};

renderAt(1)
  .then(() => {{
{fit_block}
  }})
  .catch((err) => console.error("vega-embed error:", err));
"""


# Opt-in interactive embed for charts that need selections. `data-external`
# tells Quarto not to inline the ESM package into embed-resources output; keeping
# it at its CDN origin also keeps all of Vega's relative module imports valid.
def esm_vega_renderer(spec, div_id=None, responsive=False, **metadata):
    # Resolve the wrapper id BEFORE compile_with_vegafusion, which nulls the
    # top-level `name`. Precedence: explicit div_id > chart name > random uuid.
    div_id = div_id or spec.get("name") or ("vega-" + uuid.uuid4().hex)
    # With the vegafusion data transformer, the spec handed to renderers still
    # contains vegafusion+dataset:// placeholders; built-in renderers resolve
    # them via compile_with_vegafusion, so this renderer must too.
    if using_vegafusion():
        spec = compile_with_vegafusion(spec)
    spec_json = json.dumps(spec)
    view_id = div_id + "-view"
    controls_id = div_id + "-controls"
    html = (
        f'<div id="{div_id}" class="vega-embed-esm">\n'
        f'  <div id="{controls_id}" class="vega-controls"></div>\n'
        f'  <div id="{view_id}" class="vega-chart-view"></div>\n'
        f'</div>\n'
        f'<script type="module" data-external="1">\n'
        f'  import embed from "https://cdn.jsdelivr.net/npm/vega-embed@7/+esm";\n'
        f'  const baseSpec = {spec_json};\n'
        f'  const divId = "{div_id}";\n'
        f'  const viewId = "{view_id}";\n'
        f'  const controlsId = "{controls_id}";\n'
        f'{_RESPONSIVE_RENDER_JS if responsive else ""}'
        f'{_render_at_js(responsive)}'
        f'</script>'
    )
    return {"text/html": html}


def interactive(chart, id=None, responsive=False):
    """Render one chart with the browser-side ESM vega-embed instead of the
    static SVG default, keeping selections and tooltips alive.

    Pass ``id`` to give the wrapper div a deterministic id (e.g. for a
    driver.js tour selector) instead of a random per-render uuid.

    Pass ``responsive=True`` to re-embed the chart, rescaled to its
    container's actual width, on load and on resize, instead of rendering
    once at the spec's fixed authored size. Opt-in: most charts already fit
    their card, and re-embedding on resize drops any live selection.
    """
    from IPython.display import HTML

    # Interactive specs execute their transforms in the browser. Serialize
    # their frames as ordinary inline datasets instead of Vegafusion's
    # server-only `vegafusion+dataset://...` placeholders.
    with alt.data_transformers.enable("default", max_rows=None):
        spec = chart.to_dict(context={"pre_transform": False})
        rendered = esm_vega_renderer(spec, div_id=id, responsive=responsive)
        return HTML(rendered["text/html"])


def setup():
    """Enable the vegafusion transformer and local SVG renderer.

    Call once from the first cell of any .qmd that displays project charts.
    """
    alt.data_transformers.enable("vegafusion")
    alt.data_transformers.disable_max_rows()
    alt.renderers.register("local-svg", svg_renderer)
    alt.renderers.enable("local-svg")
