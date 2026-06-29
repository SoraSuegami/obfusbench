"""Build the static site from benchmark data."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape

from .models import DEFAULT_LABELS, Benchmark, metric_fields
from .pricing import device_display, load_gpu_registry, price_for_device, resolve_prices
from .utils import commit_url, format_number, format_sci, format_sci_p

# Total-time metrics whose cells also show derived cost (price x total time).
COST_METRIC_KEYS = ("obfuscation_total_time_hours", "evaluation_total_time_hours")

# Categorical palette for breakdown segments, cycled in order; the synthetic
# "Other" remainder slice always uses the neutral grey.
BREAKDOWN_PALETTE = (
    "#2563eb",  # blue (matches accent)
    "#7c3aed",  # violet
    "#0891b2",  # cyan
    "#16a34a",  # green
    "#d97706",  # amber
    "#db2777",  # pink
    "#4f46e5",  # indigo
    "#65a30d",  # lime
)
BREAKDOWN_OTHER_COLOR = "#cbd5e1"


def breakdown_rows(items, label_attr: str, value_attr: str, total: float, sigfigs=None):
    """Build display rows for a part-to-whole breakdown of ``total``.

    Returns a list of ``{label, value, pct, color, sigfigs}`` dicts, or ``None``
    when there is no breakdown data. Percentages are relative to ``total``; any
    remainder (total - sum of sub-steps) is appended as an "Other" slice so the
    segments always add up to the phase total. ``sigfigs`` is the per-item
    list of source-literal significant digits (used for display precision); the
    derived "Other" slice has no literal, so it shows at the 3-digit floor.
    """
    if not items:
        return None
    sigfigs = sigfigs or []
    rows = []
    accounted = 0.0
    for i, item in enumerate(items):
        value = getattr(item, value_attr)
        accounted += value
        rows.append(
            {
                "label": getattr(item, label_attr),
                "value": value,
                "pct": (value / total * 100.0) if total > 0 else 0.0,
                "color": BREAKDOWN_PALETTE[i % len(BREAKDOWN_PALETTE)],
                "sigfigs": sigfigs[i] if i < len(sigfigs) else None,
            }
        )
    remainder = total - accounted
    # Only surface "Other" when it is a meaningful slice (guards float noise).
    if total > 0 and remainder > total * 1e-9:
        rows.append(
            {
                "label": "Other",
                "value": remainder,
                "pct": remainder / total * 100.0,
                "color": BREAKDOWN_OTHER_COLOR,
                "sigfigs": None,
            }
        )
    return rows


def chart_tabs_for(labels: dict[str, str]) -> list[str]:
    """Chart selector tab labels, in the order charts.js renders them."""
    p1, p2, size = labels["phase1_short"], labels["phase2_short"], labels["size"]
    return [
        f"{p2} total time vs date",
        f"{p1} total time vs date",
        f"{p2} total time vs {size.lower()}",
        f"{p2} latency vs date",
        f"{p1} latency vs date",
    ]


PROTECTED_OUTPUT_DIRS = (
    ".git",
    ".github",
    "benchmarks",
    "config",
    "examples",
    "schema",
    "sitegen",
    "static",
    "templates",
    "tests",
)


def _is_relative_to(path: Path, parent: Path) -> bool:
    return path == parent or path.is_relative_to(parent)


def validate_output_dir(output_dir: Path, project_root: Path) -> Path:
    """Reject output paths where cleanup could delete repository sources."""
    resolved_output = output_dir.resolve()
    resolved_root = project_root.resolve()

    if _is_relative_to(resolved_root, resolved_output):
        raise ValueError(
            f"Refusing to build into {resolved_output}: output directory would delete "
            f"the project root {resolved_root}"
        )

    for name in PROTECTED_OUTPUT_DIRS:
        protected = resolved_root / name
        if _is_relative_to(resolved_output, protected):
            raise ValueError(
                f"Refusing to build into {resolved_output}: output directory is inside "
                f"protected source directory {protected}"
            )

    return resolved_output


def normalize_base_url(value: str | None) -> str:
    """Normalize a configured base URL/path for absolute 404 links."""
    if not value:
        return ""
    if value.startswith(("http://", "https://")):
        return value.rstrip("/") + "/"
    return "/" + value.strip("/") + "/"


def load_site_config(config_path: Path) -> dict:
    """Load site configuration from YAML."""
    with open(config_path) as f:
        return yaml.safe_load(f)


def load_targets(config: dict) -> list[dict]:
    """Read the configured benchmark targets; the first one is the default."""
    raw = config.get("targets")
    if not raw:
        return [{"id": "default", "name": config.get("benchmark_name", "Benchmark results")}]

    targets: list[dict] = []
    seen: set[str] = set()
    for entry in raw:
        if not isinstance(entry, dict) or not entry.get("id") or not entry.get("name"):
            raise ValueError(
                "each entry in config/site.yaml 'targets' must have non-empty 'id' and 'name'"
            )
        tid = str(entry["id"]).strip()
        if tid in seen:
            raise ValueError(f"duplicate target id '{tid}' in config/site.yaml")
        seen.add(tid)
        # Labels rename the two phases / size for this target; missing keys fall
        # back to the obfuscation defaults.
        labels = {**DEFAULT_LABELS, **(entry.get("labels") or {})}
        targets.append({"id": tid, "name": str(entry["name"]).strip(), "labels": labels})
    return targets


def create_jinja_env(templates_dir: Path) -> Environment:
    """Create a Jinja2 environment with autoescaping and helpers."""
    env = Environment(
        loader=FileSystemLoader(templates_dir),
        autoescape=select_autoescape(["html"]),
    )
    env.filters["format_number"] = format_number
    env.filters["format_sci"] = format_sci
    env.filters["format_sci_p"] = format_sci_p
    env.globals["commit_url"] = commit_url
    return env


def build_site(
    benchmarks: list[Benchmark],
    output_dir: Path,
    project_root: Path,
    prices: dict[str, float] | None = None,
) -> None:
    """Generate the full static site.

    ``prices`` maps a normalized GPU id to its USD/hour rate; when omitted, prices
    are resolved without network access (``fetch=False``), so they are empty and
    cost renders as ND. Cost is derived as ``price * total_time_hours`` and is
    never read from the benchmark YAML.
    """
    project_root = project_root.resolve()
    output_dir = validate_output_dir(output_dir, project_root)
    config = load_site_config(project_root / "config" / "site.yaml")
    env = create_jinja_env(project_root / "templates")

    if prices is None:
        prices, _ = resolve_prices(project_root, fetch=False)

    registry = load_gpu_registry(project_root)

    def costs_for(bm: Benchmark) -> dict[str, float | None]:
        rate = price_for_device(prices, bm.device)
        return {
            "obfuscation_total_time_hours": (
                bm.obfuscation_total_time_hours * rate if rate is not None else None
            ),
            "evaluation_total_time_hours": (
                bm.evaluation_total_time_hours * rate if rate is not None else None
            ),
        }

    # Clean and create output directory
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    # Compute base_url (empty string for relative paths)
    base_url = ""

    common_ctx = {
        "site": config,
        "base_url": base_url,
    }

    # Group benchmarks by target; entries without a target use the default
    # (first configured) target.
    targets = load_targets(config)
    default_target_id = targets[0]["id"]
    by_target: dict[str, list[Benchmark]] = {t["id"]: [] for t in targets}
    for bm in benchmarks:
        if bm.target is None:
            bm.target = default_target_id
        if bm.target not in by_target:
            raise ValueError(
                f"benchmark '{bm.id}' references unknown target '{bm.target}' "
                f"(valid targets: {', '.join(by_target)})"
            )
        by_target[bm.target].append(bm)

    # Default leaderboard order: ascending phase-1 (obfuscation) total time, so
    # the server-rendered table is already smallest-first regardless of JS.
    for tid in by_target:
        by_target[tid].sort(key=lambda b: b.obfuscation_total_time_hours)

    def chart_entry(bm: Benchmark) -> dict:
        costs = costs_for(bm)
        return {
            "id": bm.id,
            "slug": bm.slug,
            "date": bm.date.isoformat(),
            "obfuscation_latency_min": bm.obfuscation_latency_min,
            "obfuscation_total_time_hours": bm.obfuscation_total_time_hours,
            "evaluation_latency_min": bm.evaluation_latency_min,
            "evaluation_total_time_hours": bm.evaluation_total_time_hours,
            "storage_gb": bm.storage_gb,
            "device": bm.device,
            # Derived total-time cost (price x total time); null when no price.
            "obfuscation_cost_usd": costs["obfuscation_total_time_hours"],
            "evaluation_cost_usd": costs["evaluation_total_time_hours"],
        }

    # Build index page
    target_ctx = [
        {
            "id": t["id"],
            "name": t["name"],
            "labels": t["labels"],
            "metric_fields": metric_fields(t["labels"]),
            "chart_tabs": chart_tabs_for(t["labels"]),
            "benchmarks": by_target[t["id"]],
            "chart_data": [chart_entry(bm) for bm in by_target[t["id"]]],
            "costs_by_slug": {bm.slug: costs_for(bm) for bm in by_target[t["id"]]},
            "device_by_slug": {
                bm.slug: device_display(registry, bm.device) for bm in by_target[t["id"]]
            },
        }
        for t in targets
    ]
    index_tpl = env.get_template("index.html")
    index_html = index_tpl.render(
        targets=target_ctx, total_count=len(benchmarks), **common_ctx
    )
    (output_dir / "index.html").write_text(index_html)

    # Build detail pages
    target_names = {t["id"]: t["name"] for t in targets}
    target_labels = {t["id"]: t["labels"] for t in targets}
    impl_dir = output_dir / "implementations"
    detail_tpl = env.get_template("implementation.html")
    for bm in benchmarks:
        page_dir = impl_dir / bm.slug
        page_dir.mkdir(parents=True)
        costs = costs_for(bm)
        # Depth for relative paths: implementations/<slug>/index.html -> ../../
        detail_html = detail_tpl.render(
            benchmark=bm,
            target_name=target_names[bm.target],
            labels=target_labels[bm.target],
            base_url="../../",
            site=config,
            commit_link=commit_url(bm.implementation_url, bm.commit),
            obfuscation_cost_usd=costs["obfuscation_total_time_hours"],
            evaluation_cost_usd=costs["evaluation_total_time_hours"],
            device_label=device_display(registry, bm.device),
            device_hourly_price_usd=price_for_device(prices, bm.device),
            obfuscation_time_rows=breakdown_rows(
                bm.obfuscation_time_breakdown, "step", "time_hours",
                bm.obfuscation_total_time_hours,
                bm.display_sigfigs.get("obfuscation_time_breakdown"),
            ),
            evaluation_time_rows=breakdown_rows(
                bm.evaluation_time_breakdown, "step", "time_hours",
                bm.evaluation_total_time_hours,
                bm.display_sigfigs.get("evaluation_time_breakdown"),
            ),
            obfuscation_size_rows=breakdown_rows(
                bm.obfuscation_size_breakdown, "component", "size_gb",
                bm.storage_gb,
                bm.display_sigfigs.get("obfuscation_size_breakdown"),
            ),
        )
        (page_dir / "index.html").write_text(detail_html)

    # Build 404 page. GitHub Pages serves this file at arbitrary nested URLs,
    # so its asset and navigation links need a deployment-root base path.
    four04_tpl = env.get_template("404.html")
    four04_ctx = {**common_ctx, "base_url": normalize_base_url(config.get("pages_base_url"))}
    four04_html = four04_tpl.render(**four04_ctx)
    (output_dir / "404.html").write_text(four04_html)

    # Generate benchmarks.json
    data = []
    for bm in benchmarks:
        entry = bm.model_dump(mode="json")
        entry.pop("slug", None)
        costs = costs_for(bm)
        # Cost is derived, not stored: price x total time.
        entry["device_display"] = device_display(registry, bm.device)
        entry["device_hourly_price_usd"] = price_for_device(prices, bm.device)
        entry["obfuscation_cost_usd"] = costs["obfuscation_total_time_hours"]
        entry["evaluation_cost_usd"] = costs["evaluation_total_time_hours"]
        data.append(entry)
    (output_dir / "benchmarks.json").write_text(
        json.dumps(data, indent=2, ensure_ascii=False)
    )

    # Copy static assets
    static_src = project_root / "static"
    if static_src.is_dir():
        static_dst = output_dir / "static"
        shutil.copytree(static_src, static_dst)

    # Summary
    n = len(benchmarks)
    print(f"Built site with {n} implementation{'s' if n != 1 else ''} -> {output_dir}/")
