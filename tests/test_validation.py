"""Tests for benchmark validation and normalization."""

import pytest
from pydantic import ValidationError

from sitegen.models import Benchmark, slugify


VALID_DATA = {
    "id": "Test Implementation",
    "authors": ["Alice", "Bob"],
    "url": "https://github.com/example/repo",
    "commit": "abc1234",
    "obfuscation_latency_sec": 100.0,
    "obfuscation_cost_usd": 50.0,
    "obfuscation_peak_memory_gb": 32.0,
    "storage_gb": 256.0,
    "evaluation_latency_sec": 0.5,
    "evaluation_cost_usd": 0.01,
    "evaluation_peak_memory_gb": 2.0,
}


def test_accept_valid_yaml():
    bm = Benchmark(**VALID_DATA)
    assert bm.id == "Test Implementation"
    assert bm.slug == "test-implementation"
    assert bm.authors == ["Alice", "Bob"]


def test_normalize_authors_string():
    data = {**VALID_DATA, "authors": "Alice"}
    bm = Benchmark(**data)
    assert bm.authors == ["Alice"]


def test_normalize_commit_empty_string():
    data = {**VALID_DATA, "commit": ""}
    bm = Benchmark(**data)
    assert bm.commit is None


def test_reject_negative_metric():
    data = {**VALID_DATA, "obfuscation_latency_sec": -1.0}
    with pytest.raises(ValidationError, match="non-negative"):
        Benchmark(**data)


def test_reject_infinite_metric():
    data = {**VALID_DATA, "obfuscation_cost_usd": float("inf")}
    with pytest.raises(ValidationError, match="finite"):
        Benchmark(**data)


def test_reject_nan_metric():
    data = {**VALID_DATA, "evaluation_latency_sec": float("nan")}
    with pytest.raises(ValidationError, match="finite"):
        Benchmark(**data)


def test_reject_unknown_fields():
    data = {**VALID_DATA, "unknown_field": "surprise"}
    with pytest.raises(ValidationError, match="extra"):
        Benchmark(**data)


def test_reject_empty_id():
    data = {**VALID_DATA, "id": ""}
    with pytest.raises(ValidationError, match="non-empty"):
        Benchmark(**data)


def test_reject_invalid_url():
    data = {**VALID_DATA, "url": "ftp://not-http.example.com"}
    with pytest.raises(ValidationError, match="http"):
        Benchmark(**data)


def test_optional_url_and_commit():
    data = {**VALID_DATA}
    del data["url"]
    del data["commit"]
    bm = Benchmark(**data)
    assert bm.url is None
    assert bm.commit is None


def test_slug_derivation():
    assert slugify("My Cool iO Impl") == "my-cool-io-impl"
    assert slugify("  spaces  ") == "spaces"
    assert slugify("UPPER-case_mix") == "upper-case-mix"


def test_reject_duplicate_id(tmp_path):
    """Test duplicate id detection via the loader."""
    from sitegen.load import load_benchmarks

    f1 = tmp_path / "a.yaml"
    f2 = tmp_path / "b.yaml"

    import yaml

    f1.write_text(yaml.dump({**VALID_DATA, "id": "Same Name"}))
    f2.write_text(yaml.dump({**VALID_DATA, "id": "Same Name"}))

    with pytest.raises(SystemExit):
        load_benchmarks(tmp_path)


def test_reject_duplicate_slug(tmp_path):
    """Slug collision from different ids that produce the same slug."""
    from sitegen.load import load_benchmarks

    import yaml

    f1 = tmp_path / "a.yaml"
    f2 = tmp_path / "b.yaml"

    f1.write_text(yaml.dump({**VALID_DATA, "id": "foo-bar"}))
    f2.write_text(yaml.dump({**VALID_DATA, "id": "foo bar"}))

    with pytest.raises(SystemExit):
        load_benchmarks(tmp_path)
