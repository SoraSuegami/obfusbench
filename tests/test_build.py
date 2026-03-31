"""Tests for the site build process."""

import json
from pathlib import Path

import yaml

from sitegen.build import build_site
from sitegen.load import load_benchmarks
from sitegen.models import Benchmark


VALID_DATA = {
    "id": "Test Implementation",
    "authors": ["Alice", "Bob"],
    "url": "https://github.com/example/repo",
    "commit": "abc1234",
    "obfuscation_latency_sec": 100.0,
    "obfuscation_cost_usd": 50.0,
    "obfuscation_peak_memory_gb": 32.0,
    "obfuscated_circuit_size_gb": 256.0,
    "evaluation_latency_sec": 0.5,
    "evaluation_cost_usd": 0.01,
    "evaluation_peak_memory_gb": 2.0,
}

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def test_build_empty_benchmarks(tmp_path):
    """Build must succeed with zero benchmark files."""
    benchmarks_dir = tmp_path / "benchmarks"
    benchmarks_dir.mkdir()
    output_dir = tmp_path / "site"

    benchmarks = load_benchmarks(benchmarks_dir)
    assert benchmarks == []

    build_site(benchmarks, output_dir, PROJECT_ROOT)

    assert (output_dir / "index.html").exists()
    assert (output_dir / "404.html").exists()
    assert (output_dir / "benchmarks.json").exists()

    # Check empty state text in index
    index_html = (output_dir / "index.html").read_text()
    assert "No benchmark entries yet" in index_html


def test_build_with_one_benchmark(tmp_path):
    """Build generates index, detail page, and benchmarks.json."""
    benchmarks_dir = tmp_path / "benchmarks"
    benchmarks_dir.mkdir()
    output_dir = tmp_path / "site"

    (benchmarks_dir / "test.yaml").write_text(yaml.dump(VALID_DATA))
    benchmarks = load_benchmarks(benchmarks_dir)
    assert len(benchmarks) == 1

    build_site(benchmarks, output_dir, PROJECT_ROOT)

    # Index
    assert (output_dir / "index.html").exists()
    index_html = (output_dir / "index.html").read_text()
    assert "Test Implementation" in index_html

    # Detail page
    detail_path = output_dir / "implementations" / "test-implementation" / "index.html"
    assert detail_path.exists()
    detail_html = detail_path.read_text()
    assert "Test Implementation" in detail_html
    assert "Alice" in detail_html

    # benchmarks.json
    bj = json.loads((output_dir / "benchmarks.json").read_text())
    assert len(bj) == 1
    assert bj[0]["id"] == "Test Implementation"

    # 404
    assert (output_dir / "404.html").exists()

    # Static assets
    assert (output_dir / "static" / "styles.css").exists()
    assert (output_dir / "static" / "app.js").exists()


def test_benchmarks_json_no_slug(tmp_path):
    """benchmarks.json should not include the internal slug field."""
    benchmarks_dir = tmp_path / "benchmarks"
    benchmarks_dir.mkdir()
    output_dir = tmp_path / "site"

    (benchmarks_dir / "test.yaml").write_text(yaml.dump(VALID_DATA))
    benchmarks = load_benchmarks(benchmarks_dir)
    build_site(benchmarks, output_dir, PROJECT_ROOT)

    bj = json.loads((output_dir / "benchmarks.json").read_text())
    assert "slug" not in bj[0]
