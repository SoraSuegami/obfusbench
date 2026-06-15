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

    // Scientific notation matching the leaderboard table (e.g. "4.42e+46").
    function formatSci(v) {
        return Number(v).toExponential(2);
    }

    // Per-target display labels (renames the two phases / size); fields keys are
    // shared across targets so only the text differs.
    var DEFAULT_LABELS = {
        phase1_short: "Obf.",
        phase1_full: "Obfuscation",
        phase2_short: "Eval.",
        phase2_full: "Evaluation",
        size: "Obfuscation size",
    };

    // Each spec maps a benchmark to an {x, y} point plus axis metadata. Text is
    // built from the target's labels; structure (point accessors, goals, axes)
    // is identical for every target. "goal" draws a horizontal line marking the
    // ideal target value; those charts use a logarithmic y-axis so the goal
    // stays visible next to astronomically larger measurements.
    function buildSpecs(L) {
        return [
            {
                xTitle: "Date",
                yTitle: L.phase2_full + " total time (hours)",
                xIsDate: true,
                goal: 1,
                goalLabel: "Goal: 1 hour",
                // Derived cost shown in the tooltip (total-time charts only).
                costKey: "evaluation_cost_usd",
                point: function (b) {
                    return { x: dateToTs(b.date), y: b.evaluation_total_time_hours };
                },
            },
            {
                xTitle: "Date",
                yTitle: L.phase1_full + " total time (hours)",
                xIsDate: true,
                goal: 1000,
                goalLabel: "Goal: 1000 hours",
                costKey: "obfuscation_cost_usd",
                point: function (b) {
                    return { x: dateToTs(b.date), y: b.obfuscation_total_time_hours };
                },
            },
            {
                xTitle: L.size + " (GB)",
                yTitle: L.phase2_full + " total time (hours)",
                xIsDate: false,
                // Diagonal goal line connecting 1000 GB on the x-axis with
                // 1 hour on the y-axis.
                goalX: 1000,
                goalY: 1,
                goalLabel: "Goal: 1000 GB, 1 hour",
                costKey: "evaluation_cost_usd",
                point: function (b) {
                    return { x: b.storage_gb, y: b.evaluation_total_time_hours };
                },
            },
            {
                xTitle: "Date",
                yTitle: L.phase2_full + " latency (mins)",
                xIsDate: true,
                point: function (b) {
                    return { x: dateToTs(b.date), y: b.evaluation_latency_sec / 60 };
                },
            },
            {
                xTitle: "Date",
                yTitle: L.phase1_full + " latency (mins)",
                xIsDate: true,
                point: function (b) {
                    return { x: dateToTs(b.date), y: b.obfuscation_latency_sec / 60 };
                },
            },
        ];
    }

    // Draws a dashed goal line: horizontal at y when only y is given, or
    // diagonal connecting x on the bottom axis with y on the left axis.
    var goalLinePlugin = {
        id: "goalLine",
        afterDatasetsDraw: function (chart) {
            var opts = chart.options.plugins.goalLine;
            if (!opts || opts.y == null) return;
            var area = chart.chartArea;
            var ctx = chart.ctx;

            ctx.save();
            // Keep the goal line inside the plot area while zooming/panning.
            ctx.beginPath();
            ctx.rect(area.left, area.top, area.right - area.left, area.bottom - area.top);
            ctx.clip();
            ctx.strokeStyle = "#16a34a";
            ctx.lineWidth = 2;
            ctx.setLineDash([8, 5]);
            ctx.font = "600 12px " + (Chart.defaults.font.family || "sans-serif");
            ctx.fillStyle = "#16a34a";

            var y = chart.scales.y.getPixelForValue(opts.y);
            if (opts.x != null) {
                // Diagonal between the points where the goal values meet the
                // (unzoomed) axes. Anchoring to data coordinates keeps the
                // line in place while the user zooms or pans.
                var pad = opts.pad || 100;
                var x0 = chart.scales.x.getPixelForValue(opts.x);
                var y0 = chart.scales.y.getPixelForValue(opts.y / pad);
                var x1 = chart.scales.x.getPixelForValue(opts.x / pad);
                var y1 = chart.scales.y.getPixelForValue(opts.y);
                if (isFinite(x0) && isFinite(y0) && isFinite(x1) && isFinite(y1)) {
                    ctx.beginPath();
                    ctx.moveTo(x0, y0);
                    ctx.lineTo(x1, y1);
                    ctx.stroke();
                    ctx.setLineDash([]);
                    ctx.textAlign = "left";
                    ctx.textBaseline = "middle";
                    ctx.fillText(
                        opts.label,
                        (x0 + x1) / 2 + 10,
                        (y0 + y1) / 2 - 10
                    );
                }
            } else if (isFinite(y) && y >= area.top && y <= area.bottom) {
                ctx.beginPath();
                ctx.moveTo(area.left, y);
                ctx.lineTo(area.right, y);
                ctx.stroke();
                ctx.setLineDash([]);
                ctx.textAlign = "right";
                ctx.textBaseline = "bottom";
                ctx.fillText(opts.label, area.right - 6, y - 4);
            }
            ctx.restore();
        },
    };
    Chart.register(goalLinePlugin);

    // chartjs-plugin-zoom auto-registers from its UMD bundle; this is a
    // harmless safety net in case a future build stops doing so.
    if (typeof window !== "undefined" && window.ChartZoom) {
        Chart.register(window.ChartZoom);
    }

    // Label only powers of ten on logarithmic axes (e.g. "1e+38").
    function logTickLabel(value) {
        if (value <= 0) return "";
        var exp = Math.log10(value);
        if (Math.abs(exp - Math.round(exp)) > 1e-9) return "";
        exp = Math.round(exp);
        if (exp >= 0 && exp <= 3) return String(Math.pow(10, exp));
        return "1e" + (exp > 0 ? "+" : "") + exp;
    }

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

        // Per-target display labels drive the chart titles for this panel.
        var labels = DEFAULT_LABELS;
        var labelsEl = panel.querySelector(".chart-labels");
        if (labelsEl) {
            try {
                labels = Object.assign({}, DEFAULT_LABELS, JSON.parse(labelsEl.textContent));
            } catch (e) {
                labels = DEFAULT_LABELS;
            }
        }
        var SPECS = buildSpecs(labels);

        var chart = null;
        var activeSpec = 0;

        function render(specIndex) {
            activeSpec = specIndex;
            var spec = SPECS[specIndex];
            var points = data.map(function (b) {
                var p = spec.point(b);
                p.id = b.id;
                // Carry cost for total-time charts (spec.costKey set).
                if (spec.costKey) {
                    p.device = b.device;
                    p.cost = b[spec.costKey];
                }
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

            // Place date-axis ticks exactly on the plotted dates (midnight UTC)
            // so each point sits on its own gridline/label.
            var dateTickValues = spec.xIsDate
                ? points.map(function (p) { return p.x; })
                : [];

            // Date axis: label whole days only, and never repeat a day. Ticks
            // whose day matches the previous tick's day are dropped, so the
            // smallest visible label unit is one day.
            var xTicks = spec.xIsDate
                ? {
                    callback: function (value, index, ticks) {
                        var label = tsToLabel(value);
                        if (index > 0 && ticks[index - 1] &&
                            tsToLabel(ticks[index - 1].value) === label) {
                            return null;
                        }
                        return label;
                    },
                }
                : {};

            // Goal charts use log axes so the goal line and the (much
            // larger) measured values fit on the same chart. Pad the range
            // a decade past the goal so the line sits inside the plot area.
            // Diagonal-goal charts get two decades of padding so the
            // segment near the origin corner stays legible.
            var goalPad = spec.goalX != null ? 100 : 10;
            var yGoal = spec.goal != null ? spec.goal : spec.goalY;
            var yScale = yGoal != null
                ? {
                    type: "logarithmic",
                    suggestedMin: yGoal / goalPad,
                    title: { display: true, text: spec.yTitle },
                    ticks: { callback: logTickLabel },
                }
                : {
                    type: "linear",
                    beginAtZero: true,
                    title: { display: true, text: spec.yTitle },
                };
            var xScale = spec.goalX != null
                ? {
                    type: "logarithmic",
                    suggestedMin: spec.goalX / goalPad,
                    title: { display: true, text: spec.xTitle },
                    ticks: { callback: logTickLabel },
                }
                : {
                    type: "linear",
                    title: { display: true, text: spec.xTitle },
                    ticks: xTicks,
                    // Force ticks onto the actual data dates (within the current
                    // zoom range) so points land exactly on their gridlines.
                    afterBuildTicks: spec.xIsDate
                        ? function (scale) {
                            scale.ticks = dateTickValues
                                .filter(function (v) {
                                    return v >= scale.min && v <= scale.max;
                                })
                                .map(function (v) { return { value: v }; });
                        }
                        : undefined,
                };

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
                    // No entry animation: programmatic zooms (fit-to-data)
                    // race against the animator and end up with stale
                    // element positions.
                    animation: false,
                    // Reserve a top band so the floating view controls
                    // (top-right) never overlap plotted points or lines.
                    layout: { padding: { top: 44 } },
                    plugins: {
                        legend: { display: false },
                        goalLine: yGoal != null
                            ? { x: spec.goalX, y: yGoal, pad: goalPad, label: spec.goalLabel }
                            : { y: null },
                        zoom: {
                            // Map-style navigation: drag to pan, wheel/pinch
                            // to zoom around the cursor.
                            pan: { enabled: true, mode: "xy" },
                            zoom: {
                                wheel: { enabled: true },
                                pinch: { enabled: true },
                                mode: "xy",
                            },
                        },
                        tooltip: {
                            callbacks: {
                                label: function (ctx) {
                                    var raw = ctx.raw;
                                    var xLabel = spec.xIsDate
                                        ? tsToLabel(raw.x)
                                        : raw.x;
                                    var lines = [
                                        raw.id +
                                        " (" +
                                        spec.xTitle +
                                        ": " +
                                        xLabel +
                                        ", " +
                                        spec.yTitle +
                                        ": " +
                                        raw.y +
                                        ")",
                                    ];
                                    // Total-time charts also show derived cost.
                                    if (spec.costKey && raw.device) {
                                        lines.push(
                                            "Cost: " +
                                            (raw.cost != null
                                                ? "$" + formatSci(raw.cost)
                                                : "ND")
                                        );
                                    }
                                    return lines;
                                },
                            },
                        },
                    },
                    scales: {
                        x: xScale,
                        y: yScale,
                    },
                },
            };

            if (chart) chart.destroy();
            chart = new Chart(canvas, config);
        }

        function resetZoom() {
            if (chart && typeof chart.resetZoom === "function") chart.resetZoom();
        }

        // Pad a data bounding box so the points don't sit on the chart edge.
        // Log axes get a fixed multiplicative margin; linear axes a relative
        // one, with a fallback window when all points share one value.
        function paddedRange(min, max, isLog, isDate) {
            if (isLog) {
                return { min: Math.max(min / 3, Number.MIN_VALUE), max: max * 3 };
            }
            var pad = (max - min) * 0.08;
            if (pad === 0) {
                pad = isDate ? 30 * 24 * 3600 * 1000 : Math.max(Math.abs(max) * 0.1, 1);
            }
            return { min: min - pad, max: max + pad };
        }

        // Zoom straight to the bounding box of the plotted benchmarks,
        // leaving the goal line out of view if it is far away.
        function fitToData() {
            if (!chart || typeof chart.zoomScale !== "function") return;
            var pts = chart.data.datasets[0].data;
            if (!pts.length) return;
            var xmin = Infinity, xmax = -Infinity, ymin = Infinity, ymax = -Infinity;
            pts.forEach(function (p) {
                if (p.x < xmin) xmin = p.x;
                if (p.x > xmax) xmax = p.x;
                if (p.y < ymin) ymin = p.y;
                if (p.y > ymax) ymax = p.y;
            });
            var spec = SPECS[activeSpec];
            var scales = chart.options.scales;
            chart.zoomScale(
                "x",
                paddedRange(xmin, xmax, scales.x.type === "logarithmic", spec.xIsDate),
                "none"
            );
            chart.zoomScale(
                "y",
                paddedRange(ymin, ymax, scales.y.type === "logarithmic", false),
                "none"
            );
        }

        var resetBtn = panel.querySelector(".chart-reset");
        if (resetBtn) resetBtn.addEventListener("click", resetZoom);
        var fitBtn = panel.querySelector(".chart-fit");
        if (fitBtn) fitBtn.addEventListener("click", fitToData);
        canvas.addEventListener("dblclick", resetZoom);

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
