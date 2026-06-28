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
    "device": "H100",
    "obfuscation_latency_sec": 100.0,
    "obfuscation_total_time_hours": 1.0,
    "obfuscation_peak_memory_gb": 32.0,
    "storage_gb": 256.0,
    "evaluation_latency_sec": 0.5,
    "evaluation_total_time_hours": 0.1,
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


def test_build_omits_nd_cost_and_peak_memory_cards(tmp_path):
    """Cost / peak-memory cards are omitted (not shown as ND) when unavailable.

    Peak memory is unset here and no prices are resolved, so neither card has a
    value; both are dropped from the detail page rather than rendered as ND.
    """
    benchmarks_dir = tmp_path / "benchmarks"
    benchmarks_dir.mkdir()
    output_dir = tmp_path / "site"

    data = {**VALID_DATA}
    del data["obfuscation_peak_memory_gb"]
    del data["evaluation_peak_memory_gb"]
    (benchmarks_dir / "test.yaml").write_text(yaml.dump(data))

    benchmarks = load_benchmarks(benchmarks_dir)
    build_site(benchmarks, output_dir, PROJECT_ROOT)

    detail_html = (
        output_dir / "implementations" / "test-implementation" / "index.html"
    ).read_text()
    # No ND placeholders, and the two cards are gone entirely.
    assert "ND" not in detail_html
    assert "Peak memory" not in detail_html
    assert ">Cost<" not in detail_html

    bj = json.loads((output_dir / "benchmarks.json").read_text())
    assert bj[0]["obfuscation_peak_memory_gb"] is None
    assert bj[0]["evaluation_peak_memory_gb"] is None


def test_build_shows_cost_and_peak_memory_when_available(tmp_path):
    """When a price and peak memory exist, both cards render with values."""
    benchmarks_dir = tmp_path / "benchmarks"
    benchmarks_dir.mkdir()
    output_dir = tmp_path / "site"

    (benchmarks_dir / "test.yaml").write_text(yaml.dump(VALID_DATA))
    benchmarks = load_benchmarks(benchmarks_dir)
    # price map is keyed by normalized GPU id (see pricing.normalize_key).
    build_site(benchmarks, output_dir, PROJECT_ROOT, prices={"h100": 2.0})

    detail_html = (
        output_dir / "implementations" / "test-implementation" / "index.html"
    ).read_text()
    assert "Peak memory" in detail_html
    assert ">Cost<" in detail_html
    assert "ND" not in detail_html


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

def test_build_renders_breakdown_with_other_slice(tmp_path):
    """A time breakdown renders the bar + table and an auto 'Other' remainder."""
    benchmarks_dir = tmp_path / "benchmarks"
    benchmarks_dir.mkdir()
    output_dir = tmp_path / "site"

    data = {
        **VALID_DATA,
        # total time is 1.0; sub-steps sum to 0.9, so Other = 0.1 (10%).
        "obfuscation_time_breakdown": [
            {"step": "Trapdoor sampling", "time_hours": 0.6},
            {"step": "Matrix encoding", "time_hours": 0.3},
        ],
    }
    (benchmarks_dir / "test.yaml").write_text(yaml.dump(data))
    benchmarks = load_benchmarks(benchmarks_dir)
    build_site(benchmarks, output_dir, PROJECT_ROOT)

    detail_html = (
        output_dir / "implementations" / "test-implementation" / "index.html"
    ).read_text()
    assert "Obfuscation time breakdown" in detail_html
    assert "Trapdoor sampling" in detail_html
    assert "breakdown-bar" in detail_html
    # Remainder surfaces as an "Other" slice.
    assert "Other" in detail_html


def test_build_no_breakdown_section_when_absent(tmp_path):
    """Without breakdown data, no breakdown markup is emitted."""
    benchmarks_dir = tmp_path / "benchmarks"
    benchmarks_dir.mkdir()
    output_dir = tmp_path / "site"

    (benchmarks_dir / "test.yaml").write_text(yaml.dump(VALID_DATA))
    benchmarks = load_benchmarks(benchmarks_dir)
    build_site(benchmarks, output_dir, PROJECT_ROOT)

    detail_html = (
        output_dir / "implementations" / "test-implementation" / "index.html"
    ).read_text()
    assert "breakdown-bar" not in detail_html


def test_breakdown_rows_fills_other_and_computes_pct():
    from sitegen.build import breakdown_rows
    from sitegen.models import TimeBreakdownItem

    items = [
        TimeBreakdownItem(step="A", time_hours=6.0),
        TimeBreakdownItem(step="B", time_hours=3.0),
    ]
    rows = breakdown_rows(items, "step", "time_hours", 10.0)
    assert [r["label"] for r in rows] == ["A", "B", "Other"]
    assert rows[0]["pct"] == pytest.approx(60.0)
    assert rows[-1]["label"] == "Other"
    assert rows[-1]["value"] == pytest.approx(1.0)
    assert rows[-1]["pct"] == pytest.approx(10.0)


def test_breakdown_rows_none_when_empty():
    from sitegen.build import breakdown_rows

    assert breakdown_rows(None, "step", "time_hours", 10.0) is None
    assert breakdown_rows([], "step", "time_hours", 10.0) is None


def test_breakdown_rows_no_other_when_exact():
    from sitegen.build import breakdown_rows
    from sitegen.models import SizeBreakdownItem

    items = [
        SizeBreakdownItem(component="X", size_gb=7.0),
        SizeBreakdownItem(component="Y", size_gb=3.0),
    ]
    rows = breakdown_rows(items, "component", "size_gb", 10.0)
    assert [r["label"] for r in rows] == ["X", "Y"]


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
