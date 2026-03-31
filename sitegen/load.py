"""Load and validate benchmark YAML files."""

from __future__ import annotations

import sys
from pathlib import Path

import yaml
from pydantic import ValidationError

from .models import Benchmark


def load_benchmarks(benchmarks_dir: Path) -> list[Benchmark]:
    """Load all YAML files from the benchmarks directory.

    Returns validated Benchmark objects sorted by id for deterministic output.
    Prints contributor-friendly errors and exits on failure.
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

        try:
            bm = Benchmark(**data)
            benchmarks.append(bm)
        except ValidationError as e:
            for err in e.errors():
                loc = " -> ".join(str(l) for l in err["loc"])
                errors.append(f"{path}: {loc}: {err['msg']}")

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
