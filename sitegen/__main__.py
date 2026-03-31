"""CLI entry point: python -m sitegen [validate|build]."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .build import build_site
from .load import load_benchmarks
from .models import generate_json_schema


def find_project_root() -> Path:
    """Find the project root by looking for pyproject.toml."""
    current = Path(__file__).resolve().parent.parent
    if (current / "pyproject.toml").exists():
        return current
    # Fallback to cwd
    return Path.cwd()


def cmd_validate(args: argparse.Namespace) -> None:
    project_root = find_project_root()
    benchmarks_dir = project_root / "benchmarks"

    print(f"Validating benchmarks in {benchmarks_dir}/ ...")
    benchmarks = load_benchmarks(benchmarks_dir)
    print(f"OK: {len(benchmarks)} benchmark(s) validated.")

    # Generate / refresh JSON schema
    schema_path = project_root / "schema" / "benchmark.schema.json"
    schema_path.parent.mkdir(parents=True, exist_ok=True)
    schema = generate_json_schema()
    schema_path.write_text(json.dumps(schema, indent=2, ensure_ascii=False) + "\n")
    print(f"Schema written to {schema_path}")


def cmd_build(args: argparse.Namespace) -> None:
    project_root = find_project_root()
    benchmarks_dir = project_root / "benchmarks"
    output_dir = Path(args.output).resolve()

    print(f"Validating benchmarks in {benchmarks_dir}/ ...")
    benchmarks = load_benchmarks(benchmarks_dir)
    print(f"OK: {len(benchmarks)} benchmark(s) validated.")

    build_site(benchmarks, output_dir, project_root)


def main() -> None:
    parser = argparse.ArgumentParser(prog="sitegen", description="ObfusBench site generator")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("validate", help="Validate all benchmark YAML files")

    build_parser = sub.add_parser("build", help="Build the static site")
    build_parser.add_argument("--output", required=True, help="Output directory")

    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
        sys.exit(1)

    if args.command == "validate":
        cmd_validate(args)
    elif args.command == "build":
        cmd_build(args)


if __name__ == "__main__":
    main()
