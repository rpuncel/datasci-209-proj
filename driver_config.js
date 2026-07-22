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
                element: "#vega-105d4866dc0f48a3b49c43ed5d8e2070 > div > svg > g > g > g > g > g.mark-group.role-scope.concat_0_group > g > g > g.mark-rect.role-mark.concat_0_marks > path:nth-child(1)",
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