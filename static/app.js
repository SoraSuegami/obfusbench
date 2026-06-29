// ObfusBench — target tabs, spotlight + client-side table sorting
(function () {
    "use strict";

    // --- Target tabs: switch which benchmark target is displayed ---
    var targetTabs = Array.prototype.slice.call(
        document.querySelectorAll(".target-tab")
    );
    var targetPanels = Array.prototype.slice.call(
        document.querySelectorAll(".target-panel")
    );

    function showTarget(targetId, updateUrl) {
        var known = targetPanels.some(function (p) {
            return p.getAttribute("data-target") === targetId;
        });
        if (!known) return;

        targetTabs.forEach(function (tab) {
            var active = tab.getAttribute("data-target") === targetId;
            tab.classList.toggle("is-active", active);
            tab.setAttribute("aria-selected", active ? "true" : "false");
        });
        targetPanels.forEach(function (panel) {
            if (panel.getAttribute("data-target") === targetId) {
                panel.removeAttribute("hidden");
                // Let charts.js lazily render this panel's chart.
                panel.dispatchEvent(new CustomEvent("target-shown"));
            } else {
                panel.setAttribute("hidden", "");
            }
        });

        if (updateUrl) {
            var url = new URL(window.location);
            url.searchParams.set("target", targetId);
            window.history.replaceState(null, "", url);
        }
    }

    targetTabs.forEach(function (tab) {
        tab.addEventListener("click", function () {
            showTarget(tab.getAttribute("data-target"), true);
        });
    });

    var initialTarget = new URLSearchParams(window.location.search).get("target");
    if (initialTarget) showTarget(initialTarget, false);

    // --- Per-target spotlight + table sorting ---

    function formatNum(v) {
        if (v === 0) return "0";
        var abs = Math.abs(v);
        if (abs >= 1e6 || abs < 0.001) return v.toExponential(2);
        if (v === Math.floor(v)) return String(Math.floor(v));
        return parseFloat(v.toFixed(4)).toString();
    }

    // Numeric sort keys (must match the numeric column data-sort keys)
    var numericKeys = new Set([
        "obfuscation_latency_min",
        "obfuscation_total_time_hours",
        "obfuscation_peak_memory_gb",
        "storage_gb",
        "evaluation_latency_min",
        "evaluation_total_time_hours",
        "evaluation_peak_memory_gb",
    ]);

    function initPanel(panel) {
        var table = panel.querySelector(".leaderboard-table");
        if (!table) return;

        // --- Spotlight: find best eval latency ---
        // Disabled for now; re-enable by uncommenting this block and the
        // matching markup in templates/index.html.
        /*
        (function buildSpotlight() {
            var spotlight = panel.querySelector(".spotlight");
            if (!spotlight) return;

            var ths = table.querySelectorAll("thead th[data-sort]");
            var metricLabels = {};
            var metricUnits = {};
            var evalColIndex = -1;
            ths.forEach(function (th, i) {
                var key = th.getAttribute("data-sort");
                if (key === "evaluation_latency_min") evalColIndex = i;
                var label = th.textContent.trim().replace(/\s*\(.*\)\s*$/, "");
                var unitMatch = th.textContent.match(/\(([^)]+)\)/);
                metricLabels[i] = label;
                metricUnits[i] = unitMatch ? unitMatch[1] : "";
            });
            if (evalColIndex < 0) return;

            var rows = table.querySelectorAll("tbody tr");
            if (rows.length === 0) return;

            var bestRow = null;
            var bestVal = Infinity;
            rows.forEach(function (row) {
                var cell = row.cells[evalColIndex];
                var v = parseFloat(cell.getAttribute("data-value"));
                if (v < bestVal) {
                    bestVal = v;
                    bestRow = row;
                }
            });
            if (!bestRow) return;

            // Populate hero
            spotlight.querySelector(".spotlight-value").textContent = formatNum(bestVal);
            var nameLink = bestRow.cells[0].querySelector("a");
            var spotName = spotlight.querySelector(".spotlight-name");
            spotName.textContent = nameLink.textContent;
            spotName.href = nameLink.href;

            // Populate details table with all metrics except eval latency
            var tbody = spotlight.querySelector(".spotlight-table tbody");
            ths.forEach(function (th, i) {
                var key = th.getAttribute("data-sort");
                if (key === "id" || key === "authors" || key === "developers" || key === "evaluation_latency_min") return;
                var cell = bestRow.cells[i];
                if (!cell || !cell.hasAttribute("data-value")) return;

                var tr = document.createElement("tr");
                var tdLabel = document.createElement("td");
                tdLabel.textContent = metricLabels[i];
                var tdVal = document.createElement("td");
                var rawValue = cell.getAttribute("data-value");
                var isMissing = rawValue === null || rawValue === "";
                tdVal.textContent = cell.textContent.trim() + (!isMissing && metricUnits[i] ? " " + metricUnits[i] : "");
                tr.appendChild(tdLabel);
                tr.appendChild(tdVal);
                tbody.appendChild(tr);
            });

            spotlight.removeAttribute("hidden");
        })();
        */

        // --- Table sorting ---

        var thead = table.querySelector("thead");
        var tbody = table.querySelector("tbody");
        var headers = thead.querySelectorAll("th[data-sort]");

        // Read initial sort from URL; default to ascending phase-1 total time
        // ("Obf. total time" column) when no sort is specified.
        var params = new URLSearchParams(window.location.search);
        var currentSort = params.get("sort") || "obfuscation_total_time_hours";
        // Sorting is always ascending (smaller values first).
        var currentDir = "asc";

        function sortTable(key, dir) {
            var rows = Array.prototype.slice.call(tbody.querySelectorAll("tr"));
            var isNumeric = numericKeys.has(key);
            var colIndex = -1;

            headers.forEach(function (th, i) {
                if (th.getAttribute("data-sort") === key) colIndex = i;
            });
            if (colIndex < 0) return;

            rows.sort(function (a, b) {
                var cellA = a.cells[colIndex];
                var cellB = b.cells[colIndex];
                var valA, valB;

                if (isNumeric) {
                    valA = parseFloat(cellA.getAttribute("data-value"));
                    valB = parseFloat(cellB.getAttribute("data-value"));
                    if (Number.isNaN(valA) && Number.isNaN(valB)) return 0;
                    if (Number.isNaN(valA)) return 1;
                    if (Number.isNaN(valB)) return -1;
                } else {
                    valA = cellA.textContent.trim().toLowerCase();
                    valB = cellB.textContent.trim().toLowerCase();
                }

                if (valA < valB) return dir === "asc" ? -1 : 1;
                if (valA > valB) return dir === "asc" ? 1 : -1;
                return 0;
            });

            rows.forEach(function (row) {
                tbody.appendChild(row);
            });

            // Update aria-sort
            headers.forEach(function (th) {
                if (th.getAttribute("data-sort") === key) {
                    th.setAttribute("aria-sort", dir === "asc" ? "ascending" : "descending");
                } else {
                    th.setAttribute("aria-sort", "none");
                }
            });
        }

        // Apply initial sort from URL
        if (currentSort) {
            sortTable(currentSort, currentDir);
        }

        // Click handlers
        headers.forEach(function (th) {
            th.addEventListener("click", function () {
                var key = th.getAttribute("data-sort");
                // Always sort ascending (smaller values first); no descending toggle.
                currentSort = key;
                currentDir = "asc";

                sortTable(key, "asc");

                // Update URL
                var url = new URL(window.location);
                url.searchParams.set("sort", key);
                url.searchParams.set("dir", "asc");
                window.history.replaceState(null, "", url);
            });

            // Keyboard support
            th.setAttribute("tabindex", "0");
            th.addEventListener("keydown", function (e) {
                if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    th.click();
                }
            });
        });
    }

    targetPanels.forEach(initPanel);
})();
