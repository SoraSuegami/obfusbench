// ObfusBench — tabbed trend charts (Chart.js), one chart per benchmark target
(function () {
    "use strict";

    if (typeof Chart === "undefined") return;

    // Parse "YYYY-MM-DD" into a UTC timestamp (ms) for a linear time-ish axis.
    function dateToTs(s) {
        var parts = String(s).split("-");
        return Date.UTC(
            parseInt(parts[0], 10),
            parseInt(parts[1], 10) - 1,
            parseInt(parts[2], 10)
        );
    }

    function tsToLabel(ts) {
        var d = new Date(ts);
        var m = String(d.getUTCMonth() + 1).padStart(2, "0");
        var day = String(d.getUTCDate()).padStart(2, "0");
        return d.getUTCFullYear() + "-" + m + "-" + day;
    }

    // Each spec maps a benchmark to an {x, y} point plus axis metadata.
    var SPECS = [
        {
            xTitle: "Date",
            yTitle: "Evaluation total time (hours)",
            xIsDate: true,
            point: function (b) {
                return { x: dateToTs(b.date), y: b.evaluation_total_time_hours };
            },
        },
        {
            xTitle: "Date",
            yTitle: "Obfuscation total time (hours)",
            xIsDate: true,
            point: function (b) {
                return { x: dateToTs(b.date), y: b.obfuscation_total_time_hours };
            },
        },
        {
            xTitle: "Obfuscated circuit size (GB)",
            yTitle: "Evaluation total time (hours)",
            xIsDate: false,
            point: function (b) {
                return { x: b.storage_gb, y: b.evaluation_total_time_hours };
            },
        },
        {
            xTitle: "Date",
            yTitle: "Evaluation latency (mins)",
            xIsDate: true,
            point: function (b) {
                return { x: dateToTs(b.date), y: b.evaluation_latency_sec / 60 };
            },
        },
        {
            xTitle: "Date",
            yTitle: "Obfuscation latency (mins)",
            xIsDate: true,
            point: function (b) {
                return { x: dateToTs(b.date), y: b.obfuscation_latency_sec / 60 };
            },
        },
    ];

    function initPanelCharts(panel) {
        var dataEl = panel.querySelector(".benchmark-data");
        var canvas = panel.querySelector(".chart-canvas");
        if (!dataEl || !canvas) return;

        var data;
        try {
            data = JSON.parse(dataEl.textContent);
        } catch (e) {
            return;
        }
        if (!Array.isArray(data) || data.length === 0) return;

        var chart = null;

        function render(specIndex) {
            var spec = SPECS[specIndex];
            var points = data.map(function (b) {
                var p = spec.point(b);
                p.id = b.id;
                return p;
            });

            // For date-based charts, when multiple entries share a date keep only
            // the one with the smallest y value.
            if (spec.xIsDate) {
                var bestByDate = {};
                points.forEach(function (p) {
                    var prev = bestByDate[p.x];
                    if (!prev || p.y < prev.y) bestByDate[p.x] = p;
                });
                points = Object.keys(bestByDate)
                    .map(function (k) { return bestByDate[k]; })
                    .sort(function (a, b) { return a.x - b.x; });
            }

            var xTicks = spec.xIsDate
                ? { callback: function (v) { return tsToLabel(v); } }
                : {};

            var config = {
                type: "scatter",
                data: {
                    datasets: [
                        {
                            label: spec.yTitle,
                            data: points,
                            backgroundColor: "#2563eb",
                            borderColor: "#2563eb",
                            pointRadius: 6,
                            pointHoverRadius: 8,
                            // Connect points with a dashed polyline only on
                            // date-axis charts; others stay scatter-only.
                            showLine: spec.xIsDate,
                            borderDash: [6, 4],
                            borderWidth: 2,
                            fill: false,
                            tension: 0,
                        },
                    ],
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            callbacks: {
                                label: function (ctx) {
                                    var raw = ctx.raw;
                                    var xLabel = spec.xIsDate
                                        ? tsToLabel(raw.x)
                                        : raw.x;
                                    return (
                                        raw.id +
                                        " (" +
                                        spec.xTitle +
                                        ": " +
                                        xLabel +
                                        ", " +
                                        spec.yTitle +
                                        ": " +
                                        raw.y +
                                        ")"
                                    );
                                },
                            },
                        },
                    },
                    scales: {
                        x: {
                            type: "linear",
                            title: { display: true, text: spec.xTitle },
                            ticks: xTicks,
                        },
                        y: {
                            type: "linear",
                            beginAtZero: true,
                            title: { display: true, text: spec.yTitle },
                        },
                    },
                },
            };

            if (chart) chart.destroy();
            chart = new Chart(canvas, config);
        }

        var tabs = panel.querySelectorAll(".chart-tab");
        tabs.forEach(function (tab) {
            tab.addEventListener("click", function () {
                tabs.forEach(function (t) {
                    t.classList.remove("is-active");
                    t.setAttribute("aria-selected", "false");
                });
                tab.classList.add("is-active");
                tab.setAttribute("aria-selected", "true");
                render(parseInt(tab.getAttribute("data-chart"), 10));
            });
        });

        // A canvas inside a hidden panel has zero size, so defer the first
        // render until the panel is actually shown (app.js fires the event).
        if (!panel.hasAttribute("hidden")) {
            render(0);
        } else {
            panel.addEventListener("target-shown", function onShown() {
                panel.removeEventListener("target-shown", onShown);
                if (!chart) render(0);
            });
        }
    }

    document.querySelectorAll(".target-panel").forEach(initPanelCharts);
})();
