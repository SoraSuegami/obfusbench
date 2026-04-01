// ObfusBench — spotlight + client-side table sorting
(function () {
    "use strict";

    var table = document.getElementById("leaderboard");
    if (!table) return;

    // --- Spotlight: find best eval latency ---
    (function buildSpotlight() {
        var spotlight = document.getElementById("spotlight");
        if (!spotlight) return;

        var ths = table.querySelectorAll("thead th[data-sort]");
        var metricLabels = {};
        var metricUnits = {};
        var evalColIndex = -1;
        ths.forEach(function (th, i) {
            var key = th.getAttribute("data-sort");
            if (key === "evaluation_latency_sec") evalColIndex = i;
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
        document.getElementById("spotlight-value").textContent = formatNum(bestVal);
        var nameLink = bestRow.cells[0].querySelector("a");
        var spotName = document.getElementById("spotlight-name");
        spotName.textContent = nameLink.textContent;
        spotName.href = nameLink.href;

        // Populate details table with all metrics except eval latency
        var tbody = document.querySelector("#spotlight-table tbody");
        ths.forEach(function (th, i) {
            var key = th.getAttribute("data-sort");
            if (key === "id" || key === "authors" || key === "evaluation_latency_sec") return;
            var cell = bestRow.cells[i];
            if (!cell || !cell.hasAttribute("data-value")) return;

            var tr = document.createElement("tr");
            var tdLabel = document.createElement("td");
            tdLabel.textContent = metricLabels[i];
            var tdVal = document.createElement("td");
            tdVal.textContent = cell.textContent.trim() + (metricUnits[i] ? " " + metricUnits[i] : "");
            tr.appendChild(tdLabel);
            tr.appendChild(tdVal);
            tbody.appendChild(tr);
        });

        spotlight.removeAttribute("hidden");
    })();

    function formatNum(v) {
        if (v === 0) return "0";
        var abs = Math.abs(v);
        if (abs >= 1e6 || abs < 0.001) return v.toExponential(2);
        if (v === Math.floor(v)) return String(Math.floor(v));
        return parseFloat(v.toFixed(4)).toString();
    }

    // --- Table sorting ---

    var thead = table.querySelector("thead");
    var tbody = table.querySelector("tbody");
    var headers = thead.querySelectorAll("th[data-sort]");

    // Numeric sort keys
    var numericKeys = new Set([
        "obfuscation_latency_sec",
        "obfuscation_cost_usd",
        "obfuscation_peak_memory_gb",
        "storage_gb",
        "evaluation_latency_sec",
        "evaluation_cost_usd",
        "evaluation_peak_memory_gb",
    ]);

    // Read initial sort from URL
    var params = new URLSearchParams(window.location.search);
    var currentSort = params.get("sort") || null;
    var currentDir = params.get("dir") || "asc";

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
            var dir;
            if (currentSort === key) {
                dir = currentDir === "asc" ? "desc" : "asc";
            } else {
                // Default: ascending (lower is better for metrics)
                dir = "asc";
            }
            currentSort = key;
            currentDir = dir;

            sortTable(key, dir);

            // Update URL
            var url = new URL(window.location);
            url.searchParams.set("sort", key);
            url.searchParams.set("dir", dir);
            window.history.replaceState(null, "", url);
        });

        // Keyboard support
        th.setAttribute("tabindex", "0");
        th.setAttribute("role", "columnheader button");
        th.addEventListener("keydown", function (e) {
            if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                th.click();
            }
        });
    });
})();
