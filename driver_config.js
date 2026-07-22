window.addEventListener("load", () => {
    requestAnimationFrame(() => {

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
                },
            },
            {
                element: "#tour-power-owner [class*='site_bars'] path",
                popover: {
                    title: "Hover over",
                    description: "Hover over each bar to see more details",
                }
            },
            ]
        });
        // Your DOM-safe code goes here
        console.log("The DOM is fully loaded and ready!");
        driverObj.drive();
    });

});