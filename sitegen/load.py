"""Load and validate benchmark YAML files."""

from __future__ import annotations

import sys
from pathlib import Path

import yaml
from pydantic import ValidationError

from .models import CANONICAL_METRIC_KEYS, DEFAULT_LABELS, Benchmark, yaml_key_map
from .utils import significant_digits

# Breakdown canonical field -> the per-item value sub-key whose literal carries
# the display precision.
_BREAKDOWN_VALUE_KEYS = {
    "obfuscation_time_breakdown": "time_hours",
    "evaluation_time_breakdown": "time_hours",
    "obfuscation_size_breakdown": "size_gb",
}


def _raw_scalars(node):
    """Mirror a YAML node tree as plain Python, keeping scalars as raw strings.

    Unlike ``safe_load``, scalar leaves are the original literal text (e.g.
    ``"6.695e46"``), so the contributor's written precision is preserved.
    """
    if isinstance(node, yaml.MappingNode):
        return {key.value: _raw_scalars(val) for key, val in node.value}
    if isinstance(node, yaml.SequenceNode):
        return [_raw_scalars(item) for item in node.value]
    return node.value  # ScalarNode: the raw literal string


def _sigfig_map(raw, key_map: dict[str, str]) -> dict:
    """Map each canonical field to the significant digits of its source literal.

    Latency is stored under the minutes field regardless of the unit supplied;
    breakdown fields map to a per-item list of significant-digit counts.
    """
    sf: dict = {}
    if not isinstance(raw, dict):
        return sf
    for ykey, canonical in key_map.items():
        if ykey not in raw:
            continue
        rawval = raw[ykey]
        if canonical in _BREAKDOWN_VALUE_KEYS:
            sub = _BREAKDOWN_VALUE_KEYS[canonical]
            if isinstance(rawval, list):
                sf[canonical] = [
                    significant_digits(item.get(sub)) if isinstance(item, dict) else None
                    for item in rawval
                ]
        else:
            # Seconds are converted to minutes; record precision on the min field.
            store = canonical.replace("_latency_sec", "_latency_min")
            sf[store] = significant_digits(rawval)
    return sf


def load_benchmarks(
    benchmarks_dir: Path,
    *,
    allowed_targets: list[str] | None = None,
    default_target: str | None = None,
    target_labels: dict[str, dict] | None = None,
) -> list[Benchmark]:
    """Load all YAML files from the benchmarks directory.

    Returns validated Benchmark objects sorted by id for deterministic output.
    Prints contributor-friendly errors and exits on failure.

    When ``allowed_targets`` is given, each entry's ``target`` must be one of
    those ids; entries without a ``target`` are assigned ``default_target``.

    ``target_labels`` maps a target id to its label/key scheme. A target's metric
    keys in YAML (e.g. ``encryption_latency_sec``) are translated to canonical
    model fields; using another target's keys is rejected. When omitted, the
    canonical (obfuscation) keys are assumed for every file.
    """
    if not benchmarks_dir.is_dir():
        print(f"Error: benchmarks directory not found: {benchmarks_dir}")
        sys.exit(1)

    yaml_files = sorted(
        p for p in benchmarks_dir.iterdir()
        if p.suffix in (".yaml", ".yml") and p.name != ".gitkeep"
    )

    benchmarks: list[Benchmark] = []
    errors: list[str] = []

    for path in yaml_files:
        try:
            text = path.read_text()
            data = yaml.safe_load(text)
            # Parallel node tree, used to read the raw numeric literals so the
            # site can display each value at the precision it was written with.
            raw_node = yaml.compose(text, Loader=yaml.SafeLoader)
            raw = _raw_scalars(raw_node) if raw_node is not None else {}
        except yaml.YAMLError as e:
            errors.append(f"{path}: YAML parse error: {e}")
            continue

        if data is None:
            errors.append(f"{path}: file is empty")
            continue

        if not isinstance(data, dict):
            errors.append(f"{path}: expected a YAML mapping, got {type(data).__name__}")
            continue

        # Resolve this file's target to pick its key scheme, then translate the
        # target's metric keys to the canonical model field names.
        raw_target = data.get("target")
        tid = (
            raw_target.strip()
            if isinstance(raw_target, str) and raw_target.strip()
            else default_target
        )
        labels = (target_labels or {}).get(tid) or DEFAULT_LABELS
        key_map = yaml_key_map(labels)
        # canonical -> this target's key, for translating error messages back.
        reverse = {canonical: tkey for tkey, canonical in key_map.items()}
        # Canonical names that are not this target's keys must not appear.
        forbidden = set(CANONICAL_METRIC_KEYS) - set(key_map)

        wrong_keys = [k for k in data if k in forbidden]
        if wrong_keys:
            for k in wrong_keys:
                errors.append(
                    f"{path}: '{k}' is not a valid field for target '{tid}'; "
                    f"use '{reverse.get(k, k)}'"
                )
            continue

        remapped = {key_map.get(k, k): v for k, v in data.items()}

        try:
            bm = Benchmark(**remapped)
        except ValidationError as e:
            for err in e.errors():
                loc = " -> ".join(reverse.get(str(l), str(l)) for l in err["loc"])
                errors.append(f"{path}: {loc}: {err['msg']}")
            continue

        # Record the source precision of each numeric field for display.
        bm.display_sigfigs = _sigfig_map(raw, key_map)

        if bm.target is None:
            bm.target = default_target
        if allowed_targets is not None and bm.target is not None and bm.target not in allowed_targets:
            errors.append(
                f"{path}: target: unknown target '{bm.target}' "
                f"(valid targets: {', '.join(allowed_targets)})"
            )
            continue
        benchmarks.append(bm)

    # Check for duplicate ids
    seen_ids: dict[str, str] = {}
    for bm in benchmarks:
        if bm.id in seen_ids:
            errors.append(
                f"Duplicate id '{bm.id}' found in multiple files"
            )
        else:
            seen_ids[bm.id] = bm.slug

    # Check for duplicate slugs (derived from different ids)
    seen_slugs: dict[str, str] = {}
    for bm in benchmarks:
        if bm.slug in seen_slugs and seen_slugs[bm.slug] != bm.id:
            errors.append(
                f"Slug collision: '{bm.id}' and '{seen_slugs[bm.slug]}' "
                f"both produce slug '{bm.slug}'"
            )
        else:
            seen_slugs[bm.slug] = bm.id

    if errors:
        print("Validation errors:")
        for err in errors:
            print(f"  - {err}")
        sys.exit(1)

    # Sort deterministically by id
    benchmarks.sort(key=lambda b: b.id)
    return benchmarks
