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
            // name. (The old `site_bars` chart is no longer on the page.) The
            // marks themselves live in a nested `_marks`-suffixed group: `cursor`
            // on the mark makes Vega-Lite emit a `path.background` hit-area first,
            // so a bare `path` selector spotlights that invisible rect instead of
            // an actual bar.
            element: "#ai-economy-explorer [class*='owner_power_bars_marks'] path",
                    id: "hover-bars-power",
                    popover: {
                        title: "Explore the data",
                        description: "Hover over a bar to see more details.",
                    },
                },
                {
                    element: "#tour-trigger",
                    popover: {
                        title: "test"
                    },
                    onButtonClick: (element, hint, { hints: instance }) => {
                    instance.close();
                    tour.drive();
                    },
                }
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

    // Generic "wait for a drag" gate: a map's geo-brush is a mousedown then a
    // mouseup, possibly far from where it started, so the mouseup listener is
    // attached to the document rather than the spotlighted element itself.
    let dragMouseDownHandler = null;
    let dragMouseUpHandler = null;

    function stopWatchingDrag(element) {
        if (dragMouseDownHandler) {
            element.removeEventListener("mousedown", dragMouseDownHandler);
            dragMouseDownHandler = null;
        }
        if (dragMouseUpHandler) {
            document.removeEventListener("mouseup", dragMouseUpHandler);
            dragMouseUpHandler = null;
        }
    }

    function watchForDrag(element) {
        stopWatchingDrag(element);
        dragMouseDownHandler = () => {
            dragMouseUpHandler = () => {
                stopWatchingDrag(element);
                driverObj.moveNext();
            };
            document.addEventListener("mouseup", dragMouseUpHandler);
        };
        element.addEventListener("mousedown", dragMouseDownHandler);
    }

    // Generic "wait for a click on any mark in this group" gate. The
    // spotlighted element is the whole bar-chart group (many `path` marks),
    // so the listener is delegated rather than attached to one mark.
    let barClickHandler = null;

    function stopWatchingBarClick(element) {
        if (barClickHandler) {
            element.removeEventListener("click", barClickHandler);
            barClickHandler = null;
        }
    }

    function watchForBarClick(element) {
        stopWatchingBarClick(element);
        barClickHandler = (event) => {
            if (event.target && event.target.tagName === "path") {
                stopWatchingBarClick(element);
                driverObj.moveNext();
            }
        };
        element.addEventListener("click", barClickHandler);
    }

    // Generic "wait for a click on any button in this group" gate, for the
    // restyled timeline step buttons.
    let stepClickHandler = null;

    function stopWatchingStepClick(element) {
        if (stepClickHandler) {
            element.removeEventListener("click", stepClickHandler);
            stepClickHandler = null;
        }
    }

    function watchForStepClick(element) {
        stopWatchingStepClick(element);
        stepClickHandler = (event) => {
            if (event.target && event.target.tagName === "BUTTON") {
                stopWatchingStepClick(element);
                driverObj.moveNext();
            }
        };
        element.addEventListener("click", stepClickHandler);
    }

    function cleanup() {
        stopWatchingTooltip();
        removeFrozen();
    }

    driverObj.setConfig({
        showProgress: true,
        onDestroyed: cleanup,
        steps: [
        {
            element: "#ai-economy-explorer",
            popover: {
                title: "One linked view of the AI economy",
                description: "Capital, grid capacity, and water stress share a single linked view. Click an owner in the ranking to highlight its sites on all three maps, or drag a box on any map to re-rank owners for that region.",
                align: "start",
                side: "top",
            }
        },
        {
            element: "#ai-economy-explorer-view [class*='money_summary']",
            popover: {
                title: "Total capital",
                description: "Sums capital across every filtered site.",
            }
        },
        {
            element: "#ai-economy-explorer-view [class*='power_summary']",
            popover: {
                title: "Total power",
                description: "Sums power capacity across every filtered site.",
            }
        },
        {
            element: "#ai-economy-explorer-controls input[name='show_future_sites']",
            popover: {
                title: "Toggle proposed sites",
                description: "Show or hide proposed data centers on every map.",
                side: "bottom",
            }
        },
        {
            // Spotlight the whole map (CAPITAL_MAP_VIEW), not just the site
            // markers: the geo-brush drag works anywhere on the map, including
            // the choropleth fill, but the tour's overlay only allows
            // interaction inside the spotlighted element's bounding box.
            // Starting the drag outside the markers' box would silently fail.
            element: "#ai-economy-explorer-view [class*='capital_map_view']",
            onHighlightStarted: (element) => watchForDrag(element),
            onDeselected: (element) => element && stopWatchingDrag(element),
            popover: {
                title: "Drag to filter by region",
                description: "Drag a box here to filter all views for only area. Only this map supports drag-select, but the others will update too. Give it a try!",
            }
        },
        {
            element: "#ai-economy-explorer-view [class*='electricity_sites']",
            popover: {
                title: "Grid capacity",
                description: "Compares available power capacity by site. Note that the site selection on the left-most map applies here too.",
            }
        },
        {
            element: "#ai-economy-explorer-view [class*='water_stress_states']",
            popover: {
                title: "Water stress",
                description: "Compares water stress by state.",
            }
        },
        {
            // Keep the tight, single-bar spotlight for the hover step. The
            // marks live in a nested `_marks`-suffixed group (see the hint
            // above for why a bare `path` selector is wrong here).
            element: "#ai-economy-explorer [class*='owner_power_bars_marks'] path",
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
                description: "It shows the exact numbers for the bar you hovered. You can do this on appear on every bar and map point across the dashboard.",
                side: "right",
                align: "start",
            }
        },
        {
            element: "#ai-economy-explorer-view [class*='owner_power_bars']",
            onHighlightStarted: (element) => watchForBarClick(element),
            onDeselected: (element) => element && stopWatchingBarClick(element),
            popover: {
                title: "This view shows the company that owns the most data center capacity out of what you've filtered.",
                description: "Click a bar to filter every view to that owner. Give it a try!",
            }
        },
        {
            element: "#ai-economy-explorer-view [class*='owner_power_bars']",
            onHighlightStarted: (element) => watchForBarClick(element),
            onDeselected: (element) => element && stopWatchingBarClick(element),
            popover: {
                title: "Click another to add",
                description: "Shift-click another owner to add it to the filter.",
            }
        },
        {
            element: "#ai-economy-explorer-view [class*='site_bars']",
            onHighlightStarted: (element) => watchForBarClick(element),
            onDeselected: (element) => element && stopWatchingBarClick(element),
            popover: {
                title: "Top 10 data center sites",
                description: "See the top 10 individual data center sites out of what has been selected here. Click a site to make that site stand out on the other charts.",
            }
        },
        {
            element: "#ai-economy-explorer-controls .water-story-timeline",
            onHighlightStarted: (element) => watchForStepClick(element),
            onDeselected: (element) => element && stopWatchingStepClick(element),
            popover: {
                title: "Step through time",
                description: "Click 2030, 2050, or 2080 to see a projection.",
                side: "top",
            }
        },
        {
            // No `path` suffix: the delta bars sit in an unnamed nested layer
            // scope inside this group (only the outer layer chart is named),
            // and this group's own first path is a `.background` hit-area, so
            // spotlight the whole panel instead of one mark.
            element: "#ai-economy-explorer-view [class*='water_delta_chart']",
            popover: {
                title: "What's changing",
                description: "The 12 states with the largest forecast change.",
            }
        },
        {
            element: "#ai-economy-explorer-view [class*='owner_power_bars']",
            onHighlightStarted: (element) => watchForBarClick(element),
            onDeselected: (element) => element && stopWatchingBarClick(element),
            popover: {
                title: "Double click anywhere to clear all your filters",
                description: "Since we've added a few filters, try double clicking anywhere to clear them.",
            }
        },
        {
            element: "#ai-economy-explorer-view [class*='owner_power_bars']",
            onHighlightStarted: (element) => watchForBarClick(element),
            onDeselected: (element) => element && stopWatchingBarClick(element),
            popover: {
                title: "That ends the tour!",
                description: 'Click the "Need help" button again anytime to re-take the tour.'
            }
        }
        ]
    });
    driverObj.drive();

});
