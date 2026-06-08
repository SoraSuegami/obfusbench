// ObfusBench — tabbed trend charts (Chart.js)
(function () {
    "use strict";

    var dataEl = document.getElementById("benchmark-data");
    var canvas = document.getElementById("chart-canvas");
    if (!dataEl || !canvas || typeof Chart === "undefined") return;

    var data;
    try {
        data = JSON.parse(dataEl.textContent);
    } catch (e) {
        return;
    }
    if (!Array.isArray(data) || data.length === 0) return;

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

    var chart = null;

    function render(specIndex) {
        var spec = SPECS[specIndex];
        var points = data.map(function (b) {
            var p = spec.point(b);
            p.id = b.id;
            return p;
        });

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

    var tabs = document.querySelectorAll(".chart-tab");
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

    render(0);
})();
