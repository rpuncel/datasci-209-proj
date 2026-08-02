window.addEventListener("load", () => {
    requestAnimationFrame(() => {
        const hints = window.driverHints.hints;
        const productHints = hints({
            overlay: true,
            overlayOpacity: 0.5,
            hints: [
                {
                    // Vega emits each unit view's `name` as an SVG group class, so the
            // owner ranking in charts/explorer.py is reachable by its OWNER_BARS
            // name. (The old `site_bars` chart is no longer on the page.)
            element: "#ai-economy-explorer [class*='owner_power_bars'] path",
                    id: "hover-bars-power",
                    popover: {
                        title: "Explore the data",
                        description: "Hover over a bar to see more details.",
                    },
                },
            ],
        });

        productHints.show();
    });
});

button = document.getElementById("power-help")
button.addEventListener('click', () => {
    const driver = window.driver.js.driver;

    const driverObj = driver();

    // driver.js can only spotlight a single, *stable* element per step, but the
    // Vega/Vega-Lite tooltip (#vg-tooltip-element) is transient: it is destroyed
    // on mouseout and follows the cursor, so it can never be highlighted directly
    // (the moment you move toward the popover, it vanishes). Work around it by
    // freezing a static copy of the tooltip the instant it appears, then letting
    // driver.js spotlight that copy while the live tooltip comes and goes beneath.
    const FROZEN_ID = "tour-tooltip-frozen";
    let tooltipObserver = null;

    function removeFrozen() {
        const el = document.getElementById(FROZEN_ID);
        if (el) el.remove();
    }

    // Clone the live tooltip into a pinned, non-interactive copy with the same
    // look and position. Returns true only if a visible tooltip was captured.
    function freezeTooltip() {
        const tip = document.getElementById("vg-tooltip-element");
        if (!tip || !tip.classList.contains("visible")) return false;
        removeFrozen();
        const rect = tip.getBoundingClientRect();
        const clone = tip.cloneNode(true); // deep clone keeps the styled content
        clone.id = FROZEN_ID;
        clone.removeAttribute("class"); // detach from #vg-tooltip-element show/hide
        const cs = getComputedStyle(tip);
        const props = ["background", "backgroundColor", "color", "border",
            "borderRadius", "boxShadow", "padding", "font", "fontSize",
            "fontFamily", "lineHeight"];
        clone.style.cssText = props.map((p) => `${p}:${cs[p]}`).join(";");
        Object.assign(clone.style, {
            position: "fixed",
            left: rect.left + "px",
            top: rect.top + "px",
            margin: "0",
            pointerEvents: "none",
            zIndex: "1000000002", // above the overlay (1e9) and the live tooltip
        });
        document.body.appendChild(clone);
        return true;
    }

    function stopWatchingTooltip() {
        if (tooltipObserver) {
            tooltipObserver.disconnect();
            tooltipObserver = null;
        }
    }

    // While the hover step is active, watch for the tooltip becoming visible.
    // vega-tooltip creates #vg-tooltip-element lazily on the first hover and
    // toggles its `visible` class, so we observe the whole body. On the first
    // successful freeze, advance to the step that spotlights the frozen copy.
    function watchForTooltip() {
        stopWatchingTooltip();
        tooltipObserver = new MutationObserver(() => {
            const tip = document.getElementById("vg-tooltip-element");
            if (tip && tip.classList.contains("visible") && freezeTooltip()) {
                stopWatchingTooltip();
                driverObj.moveNext();
            }
        });
        tooltipObserver.observe(document.body, {
            childList: true,
            subtree: true,
            attributes: true,
            attributeFilter: ["class", "style"],
        });
    }

    function cleanup() {
        stopWatchingTooltip();
        removeFrozen();
    }

    driverObj.setConfig({
        showProgress: true,
        onDestroyed: cleanup,
        steps: [{
            element: "#ai-economy-explorer",
            popover: {
                title: "One linked view of the AI economy",
                description: "Capital, grid capacity, and water stress share a single linked view. Click an owner in the ranking to highlight its sites on all three maps, or drag a box on any map to re-rank owners for that region.",
                align: "start",
                side: "top",
            }
        },
        {
            // Keep the tight, single-bar spotlight for the hover step.
            element: "#ai-economy-explorer [class*='owner_power_bars'] path",
            onHighlightStarted: watchForTooltip,
            onDeselected: stopWatchingTooltip,
            popover: {
                title: "Hover for details",
                description: "Hover over the highlighted bar to see its exact numbers. Give it a try!",
            }
        },
        {
            // Spotlight the frozen copy of the tooltip the user just triggered.
            element: "#" + FROZEN_ID,
            onDeselected: removeFrozen,
            popover: {
                title: "That's the tooltip",
                description: "It shows the exact numbers for the bar you hovered. These details appear on every bar and map point across the dashboard.",
                side: "right",
                align: "start",
            }
        },
        ]
    });
    driverObj.drive();

});



