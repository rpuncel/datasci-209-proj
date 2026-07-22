window.addEventListener("load", () => {
    requestAnimationFrame(() => {
        const hints = window.driverHints.hints;
        const productHints = hints({
            overlay: true,
            overlayOpacity: 0.5,
            hints: [
                {
                    element: "#tour-power-owner [class*='site_bars'] path",
                    id: "hover-bars-power",
                    popover: {
                        title: "Export your data",
                        description: "Hover over a bar for to see more details.",
                    },
                },
                {
                    element: "#summary",
                    id: "summary",
                    beacon: { side: "left", align: "center" },
                    popover: {
                        title: "Auto-generated summary",
                        description: "This paragraph is written for you from the quarter's numbers.",
                        side: "bottom",
                    },
                },
            ],
        });

        productHints.show();
    });
});

button = document.getElementById("power-help")
button.addEventListener('click', () => {
    console.log("power-help clicked");
    const driver = window.driver.js.driver;

    const driverObj = driver();

    driverObj.setConfig({
        showProgress: true,
        steps: [{
            element: 'a[data-value="⚡ Power"]',
            popover: {
                title: "Dimension tabs",
                description: "Sese water tabs specifically",
                align: "start",
                side: "bottom",

            }
        },
        {
            element: "#tour-power-owner [class*='site_bars'] path",
            advanceOnClick: true,

            popover: {
                title: "Hover over",
                description: "Hover over each bar to see more details",
                //showButtons: ['close'],

            }
        },
        ]
    });
    driverObj.drive();

});



