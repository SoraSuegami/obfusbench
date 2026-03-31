"""Build the static site from benchmark data."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape

from .models import METRIC_FIELDS, Benchmark
from .utils import commit_url, format_number


def load_site_config(config_path: Path) -> dict:
    """Load site configuration from YAML."""
    with open(config_path) as f:
        return yaml.safe_load(f)


def create_jinja_env(templates_dir: Path) -> Environment:
    """Create a Jinja2 environment with autoescaping and helpers."""
    env = Environment(
        loader=FileSystemLoader(templates_dir),
        autoescape=select_autoescape(["html"]),
    )
    env.filters["format_number"] = format_number
    env.globals["commit_url"] = commit_url
    env.globals["metric_fields"] = METRIC_FIELDS
    return env


def build_site(benchmarks: list[Benchmark], output_dir: Path, project_root: Path) -> None:
    """Generate the full static site."""
    config = load_site_config(project_root / "config" / "site.yaml")
    env = create_jinja_env(project_root / "templates")

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

    # Build index page
    index_tpl = env.get_template("index.html")
    index_html = index_tpl.render(benchmarks=benchmarks, **common_ctx)
    (output_dir / "index.html").write_text(index_html)

    # Build detail pages
    impl_dir = output_dir / "implementations"
    detail_tpl = env.get_template("implementation.html")
    for bm in benchmarks:
        page_dir = impl_dir / bm.slug
        page_dir.mkdir(parents=True)
        # Depth for relative paths: implementations/<slug>/index.html -> ../../
        detail_html = detail_tpl.render(
            benchmark=bm,
            base_url="../../",
            site=config,
            commit_link=commit_url(bm.url, bm.commit),
        )
        (page_dir / "index.html").write_text(detail_html)

    # Build 404 page
    four04_tpl = env.get_template("404.html")
    four04_html = four04_tpl.render(**common_ctx)
    (output_dir / "404.html").write_text(four04_html)

    # Generate benchmarks.json
    data = []
    for bm in benchmarks:
        entry = bm.model_dump()
        # Ensure authors is list
        entry.pop("slug", None)
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
