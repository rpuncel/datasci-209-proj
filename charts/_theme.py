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


# Opt-in interactive embed for charts that need selections. `data-external`
# tells Quarto not to inline the ESM package into embed-resources output; keeping
# it at its CDN origin also keeps all of Vega's relative module imports valid.
def esm_vega_renderer(spec, div_id=None, **metadata):
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
        f'  embed(document.getElementById("{view_id}"), {spec_json}, '
        f'{{actions: true, renderer: "svg", '
        f'bind: document.getElementById("{controls_id}")}})\n'
        f'    .then(() => {{\n'
        f'      const controls = document.getElementById("{controls_id}");\n'
        f'      const timeline = controls.querySelector('
        f'\'input[name="water_step"]\');\n'
        f'      if (timeline) {{\n'
        f'        const nativeTimeline = timeline.closest(".vega-bind");\n'
        f'        const storyTimeline = document.createElement("div");\n'
        f'        storyTimeline.className = "water-story-timeline";\n'
        f'        storyTimeline.innerHTML = '
        f'\'<div class="water-control-label">Explore time</div>\' +\n'
        f'          \'<div class="water-story-steps"></div>\';\n'
        f'        const steps = storyTimeline.querySelector(".water-story-steps");\n'
        f'        ["Baseline", "2030", "2050", "2080"].forEach((label, index) => {{\n'
        f'          const button = document.createElement("button");\n'
        f'          button.type = "button";\n'
        f'          button.dataset.step = index;\n'
        f'          button.textContent = label;\n'
        f'          button.addEventListener("click", () => {{\n'
        f'            timeline.value = index;\n'
        f'            timeline.dispatchEvent(new Event("input", {{bubbles: true}}));\n'
        f'            timeline.dispatchEvent(new Event("change", {{bubbles: true}}));\n'
        f'          }});\n'
        f'          steps.appendChild(button);\n'
        f'        }});\n'
        f'        nativeTimeline.hidden = true;\n'
        f'        nativeTimeline.insertAdjacentElement("afterend", storyTimeline);\n'
        f'        const syncTimeline = () => {{\n'
        f'          const step = Number(timeline.value);\n'
        f'          steps.querySelectorAll("button").forEach((button, index) => '
        f'button.classList.toggle("active", index === step));\n'
        f'        }};\n'
        f'        timeline.addEventListener("input", syncTimeline);\n'
        f'        syncTimeline();\n'
        f'      }}\n'
        f'    }})\n'
        f'    .catch((err) => console.error("vega-embed error:", err));\n'
        f'</script>'
    )
    return {"text/html": html}


def interactive(chart, id=None):
    """Render one chart with the browser-side ESM vega-embed instead of the
    static SVG default, keeping selections and tooltips alive.

    Pass ``id`` to give the wrapper div a deterministic id (e.g. for a
    driver.js tour selector) instead of a random per-render uuid.
    """
    from IPython.display import HTML

    # Interactive specs execute their transforms in the browser. Serialize
    # their frames as ordinary inline datasets instead of Vegafusion's
    # server-only `vegafusion+dataset://...` placeholders.
    with alt.data_transformers.enable("default", max_rows=None):
        spec = chart.to_dict(context={"pre_transform": False})
        return HTML(esm_vega_renderer(spec, div_id=id)["text/html"])


def setup():
    """Enable the vegafusion transformer and local SVG renderer.

    Call once from the first cell of any .qmd that displays project charts.
    """
    alt.data_transformers.enable("vegafusion")
    alt.data_transformers.disable_max_rows()
    alt.renderers.register("local-svg", svg_renderer)
    alt.renderers.enable("local-svg")
