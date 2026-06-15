"""Load and validate benchmark YAML files."""

from __future__ import annotations

import sys
from pathlib import Path

import yaml
from pydantic import ValidationError

from .models import CANONICAL_METRIC_KEYS, DEFAULT_LABELS, Benchmark, yaml_key_map


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
            with open(path) as f:
                data = yaml.safe_load(f)
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
