"""Tests for the site build process."""

import json
from pathlib import Path

import pytest
import yaml

from sitegen.build import build_site, normalize_base_url, validate_output_dir
from sitegen.load import load_benchmarks
from sitegen.models import Benchmark


VALID_DATA = {
    "id": "Test Implementation",
    "authors": ["Alice", "Bob"],
    "developers": ["Carol", "Dave"],
    "url": "https://github.com/example/repo",
    "commit": "abc1234",
    "date": "2026-01-15",
    "obfuscation_latency_sec": 100.0,
    "obfuscation_total_time_hours": 1.0,
    "obfuscation_cost_usd": 50.0,
    "obfuscation_peak_memory_gb": 32.0,
    "storage_gb": 256.0,
    "evaluation_latency_sec": 0.5,
    "evaluation_total_time_hours": 0.1,
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
    assert "Carol" in detail_html

    # benchmarks.json
    bj = json.loads((output_dir / "benchmarks.json").read_text())
    assert len(bj) == 1
    assert bj[0]["id"] == "Test Implementation"

    # 404
    assert (output_dir / "404.html").exists()

    # Static assets
    assert (output_dir / "static" / "styles.css").exists()
    assert (output_dir / "static" / "app.js").exists()


def test_build_missing_peak_memory_displays_nd(tmp_path):
    """Missing peak memory fields render as ND and are exported as null."""
    benchmarks_dir = tmp_path / "benchmarks"
    benchmarks_dir.mkdir()
    output_dir = tmp_path / "site"

    data = {**VALID_DATA}
    del data["obfuscation_peak_memory_gb"]
    del data["evaluation_peak_memory_gb"]
    (benchmarks_dir / "test.yaml").write_text(yaml.dump(data))

    benchmarks = load_benchmarks(benchmarks_dir)
    build_site(benchmarks, output_dir, PROJECT_ROOT)

    index_html = (output_dir / "index.html").read_text()
    assert ">ND</td>" in index_html
    assert ">ND GB<" not in index_html

    detail_html = (
        output_dir / "implementations" / "test-implementation" / "index.html"
    ).read_text()
    assert ">ND</span>" in detail_html
    assert "ND <span class=\"unit\">GB</span>" not in detail_html

    bj = json.loads((output_dir / "benchmarks.json").read_text())
    assert bj[0]["obfuscation_peak_memory_gb"] is None
    assert bj[0]["evaluation_peak_memory_gb"] is None


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

def test_reject_project_root_output_dir(tmp_path):
    project_root = tmp_path / "project"
    project_root.mkdir()

    with pytest.raises(ValueError, match="project root"):
        validate_output_dir(project_root, project_root)


def test_reject_project_root_parent_output_dir(tmp_path):
    project_root = tmp_path / "project"
    project_root.mkdir()

    with pytest.raises(ValueError, match="project root"):
        validate_output_dir(tmp_path, project_root)


def test_reject_protected_source_output_dir(tmp_path):
    project_root = tmp_path / "project"
    protected = project_root / "sitegen"
    protected.mkdir(parents=True)

    with pytest.raises(ValueError, match="protected source directory"):
        validate_output_dir(protected / "generated", project_root)


def test_allow_site_output_dir(tmp_path):
    project_root = tmp_path / "project"
    project_root.mkdir()

    assert validate_output_dir(project_root / "site", project_root) == project_root / "site"


def test_normalize_base_url():
    assert normalize_base_url("/obfusbench/") == "/obfusbench/"
    assert normalize_base_url("obfusbench") == "/obfusbench/"
    assert normalize_base_url("https://example.com/docs") == "https://example.com/docs/"


def test_404_uses_configured_pages_base_url(tmp_path):
    benchmarks_dir = tmp_path / "benchmarks"
    benchmarks_dir.mkdir()
    output_dir = tmp_path / "site"

    benchmarks = load_benchmarks(benchmarks_dir)
    build_site(benchmarks, output_dir, PROJECT_ROOT)

    html = (output_dir / "404.html").read_text()
    assert 'href="/obfusbench/static/styles.css"' in html
    assert 'href="/obfusbench/"' in html


def test_index_has_target_tabs_and_panels(tmp_path):
    """Index renders one tab and one panel per configured target."""
    benchmarks_dir = tmp_path / "benchmarks"
    benchmarks_dir.mkdir()
    output_dir = tmp_path / "site"

    (benchmarks_dir / "test.yaml").write_text(yaml.dump(VALID_DATA))
    benchmarks = load_benchmarks(benchmarks_dir)
    build_site(benchmarks, output_dir, PROJECT_ROOT)

    index_html = (output_dir / "index.html").read_text()
    assert "Obfuscated PRF for 110 input bits" in index_html
    assert "Witness encryption for 64 witness bits" in index_html
    assert index_html.count('<button type="button" class="target-tab') == 2
    assert index_html.count('class="target-panel"') == 2
    # The second (non-default) target panel starts hidden.
    assert 'data-target="witness-encryption-64" role="tabpanel" hidden' in index_html
    # The entry has no explicit target, so it lands on the default target
    # and the second panel shows the empty state.
    assert "No benchmark entries yet" in index_html


def test_benchmark_assigned_to_explicit_target(tmp_path):
    benchmarks_dir = tmp_path / "benchmarks"
    benchmarks_dir.mkdir()
    output_dir = tmp_path / "site"

    data = {**VALID_DATA, "target": "witness-encryption-64"}
    (benchmarks_dir / "test.yaml").write_text(yaml.dump(data))
    benchmarks = load_benchmarks(benchmarks_dir)
    build_site(benchmarks, output_dir, PROJECT_ROOT)

    bj = json.loads((output_dir / "benchmarks.json").read_text())
    assert bj[0]["target"] == "witness-encryption-64"

    # Default target panel is now the empty one.
    index_html = (output_dir / "index.html").read_text()
    assert "No benchmark entries yet" in index_html

    # Detail page names the target.
    detail_html = (
        output_dir / "implementations" / "test-implementation" / "index.html"
    ).read_text()
    assert "Witness encryption for 64 witness bits" in detail_html


def test_build_rejects_unknown_target(tmp_path):
    benchmarks_dir = tmp_path / "benchmarks"
    benchmarks_dir.mkdir()
    output_dir = tmp_path / "site"

    data = {**VALID_DATA, "target": "no-such-target"}
    (benchmarks_dir / "test.yaml").write_text(yaml.dump(data))
    benchmarks = load_benchmarks(benchmarks_dir)

    with pytest.raises(ValueError, match="unknown target"):
        build_site(benchmarks, output_dir, PROJECT_ROOT)
