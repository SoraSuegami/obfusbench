// ObfusBench — client-side table sorting
(function () {
    "use strict";

    var table = document.getElementById("leaderboard");
    if (!table) return;

    var thead = table.querySelector("thead");
    var tbody = table.querySelector("tbody");
    var headers = thead.querySelectorAll("th[data-sort]");

    // Numeric sort keys
    var numericKeys = new Set([
        "obfuscation_latency_sec",
        "obfuscation_cost_usd",
        "obfuscation_peak_memory_gb",
        "obfuscated_circuit_size_gb",
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
