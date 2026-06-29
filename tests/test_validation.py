"""Tests for benchmark validation and normalization."""

import pytest
from pydantic import ValidationError

from sitegen.models import Benchmark, slugify


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


def test_accept_valid_yaml():
    bm = Benchmark(**VALID_DATA)
    assert bm.id == "Test Implementation"
    assert bm.slug == "test-implementation"
    assert bm.authors == ["Alice", "Bob"]
    assert bm.developers == ["Carol", "Dave"]


def test_normalize_authors_string():
    data = {**VALID_DATA, "authors": "Alice"}
    bm = Benchmark(**data)
    assert bm.authors == ["Alice"]


def test_normalize_developers_string():
    data = {**VALID_DATA, "developers": "Carol"}
    bm = Benchmark(**data)
    assert bm.developers == ["Carol"]


def test_normalize_commit_empty_string():
    data = {**VALID_DATA, "commit": ""}
    bm = Benchmark(**data)
    assert bm.commit is None


def test_reject_negative_metric():
    data = {**VALID_DATA, "obfuscation_latency_sec": -1.0}
    with pytest.raises(ValidationError, match="non-negative"):
        Benchmark(**data)


def test_reject_infinite_metric():
    data = {**VALID_DATA, "obfuscation_total_time_hours": float("inf")}
    with pytest.raises(ValidationError, match="finite"):
        Benchmark(**data)


def test_reject_nan_metric():
    data = {**VALID_DATA, "evaluation_latency_sec": float("nan")}
    with pytest.raises(ValidationError, match="finite"):
        Benchmark(**data)


def test_optional_peak_memory_metrics():
    data = {**VALID_DATA}
    del data["obfuscation_peak_memory_gb"]
    del data["evaluation_peak_memory_gb"]
    bm = Benchmark(**data)
    assert bm.obfuscation_peak_memory_gb is None
    assert bm.evaluation_peak_memory_gb is None


def test_reject_negative_optional_peak_memory_metric():
    data = {**VALID_DATA, "obfuscation_peak_memory_gb": -1.0}
    with pytest.raises(ValidationError, match="non-negative"):
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


def test_explicit_null_url():
    data = {**VALID_DATA, "url": None}
    bm = Benchmark(**data)
    assert bm.url is None


def test_trim_people_names():
    data = {**VALID_DATA, "authors": " Alice ", "developers": [" Carol ", "Dave"]}
    bm = Benchmark(**data)
    assert bm.authors == ["Alice"]
    assert bm.developers == ["Carol", "Dave"]


def test_reject_empty_people_names():
    data = {**VALID_DATA, "authors": ["Alice", ""]}
    with pytest.raises(ValidationError, match="non-empty names"):
        Benchmark(**data)


def test_reject_empty_people_list():
    data = {**VALID_DATA, "developers": []}
    with pytest.raises(ValidationError, match="at least one name"):
        Benchmark(**data)


def test_reject_id_with_empty_slug():
    data = {**VALID_DATA, "id": "!!!"}
    with pytest.raises(ValidationError, match="URL-safe"):
        Benchmark(**data)


def test_reject_unicode_only_id_without_ascii_slug_source():
    data = {**VALID_DATA, "id": "é"}
    with pytest.raises(ValidationError, match="ASCII"):
        Benchmark(**data)


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


def test_target_normalization():
    """target is optional, stripped, and rejects blank strings."""
    bm = Benchmark(**VALID_DATA)
    assert bm.target is None

    bm = Benchmark(**{**VALID_DATA, "target": "  obfuscated-prf-110  "})
    assert bm.target == "obfuscated-prf-110"

    with pytest.raises(ValidationError):
        Benchmark(**{**VALID_DATA, "target": "   "})


def test_loader_fills_default_target(tmp_path):
    from sitegen.load import load_benchmarks

    import yaml

    (tmp_path / "a.yaml").write_text(yaml.dump(VALID_DATA))
    benchmarks = load_benchmarks(
        tmp_path,
        allowed_targets=["obfuscated-prf-110", "witness-encryption-64"],
        default_target="obfuscated-prf-110",
    )
    assert benchmarks[0].target == "obfuscated-prf-110"


WE_LABELS = {
    "phase1_key": "encryption",
    "phase2_key": "decryption",
    "size_key": "ciphertext_size_gb",
}


def _we_data():
    """VALID_DATA re-keyed for the witness-encryption target."""
    data = {**VALID_DATA, "target": "witness-encryption-64"}
    for canonical, token in (
        ("obfuscation_latency_sec", "encryption_latency_sec"),
        ("obfuscation_total_time_hours", "encryption_total_time_hours"),
        ("obfuscation_peak_memory_gb", "encryption_peak_memory_gb"),
        ("storage_gb", "ciphertext_size_gb"),
        ("evaluation_latency_sec", "decryption_latency_sec"),
        ("evaluation_total_time_hours", "decryption_total_time_hours"),
        ("evaluation_peak_memory_gb", "decryption_peak_memory_gb"),
    ):
        data[token] = data.pop(canonical)
    return data


def test_loader_translates_target_specific_keys(tmp_path):
    """A target's YAML keys translate to canonical model fields."""
    from sitegen.load import load_benchmarks

    import yaml

    (tmp_path / "we.yaml").write_text(yaml.dump(_we_data()))
    benchmarks = load_benchmarks(
        tmp_path,
        allowed_targets=["witness-encryption-64"],
        default_target="witness-encryption-64",
        target_labels={"witness-encryption-64": WE_LABELS},
    )
    bm = benchmarks[0]
    # Seconds input is converted to the canonical minutes field.
    assert bm.obfuscation_latency_min == VALID_DATA["obfuscation_latency_sec"] / 60
    assert bm.storage_gb == VALID_DATA["storage_gb"]
    assert bm.evaluation_total_time_hours == VALID_DATA["evaluation_total_time_hours"]


def test_loader_rejects_wrong_target_keys(tmp_path):
    """Using another target's keys (canonical here) is rejected for WE."""
    from sitegen.load import load_benchmarks

    import yaml

    # Canonical obfuscation keys are not valid for the witness-encryption target.
    data = {**VALID_DATA, "target": "witness-encryption-64"}
    (tmp_path / "bad.yaml").write_text(yaml.dump(data))
    with pytest.raises(SystemExit):
        load_benchmarks(
            tmp_path,
            allowed_targets=["witness-encryption-64"],
            default_target="witness-encryption-64",
            target_labels={"witness-encryption-64": WE_LABELS},
        )


def test_latency_seconds_converted_to_minutes():
    # VALID_DATA supplies seconds; the model stores minutes (÷60).
    bm = Benchmark(**VALID_DATA)
    assert bm.obfuscation_latency_min == VALID_DATA["obfuscation_latency_sec"] / 60
    assert bm.evaluation_latency_min == VALID_DATA["evaluation_latency_sec"] / 60
    assert not hasattr(bm, "obfuscation_latency_sec")


def test_accept_latency_minutes_directly():
    data = {**VALID_DATA}
    del data["obfuscation_latency_sec"]
    del data["evaluation_latency_sec"]
    data["obfuscation_latency_min"] = 5.0
    data["evaluation_latency_min"] = 0.25
    bm = Benchmark(**data)
    assert bm.obfuscation_latency_min == 5.0
    assert bm.evaluation_latency_min == 0.25


def test_reject_both_latency_units():
    data = {**VALID_DATA, "obfuscation_latency_min": 2.0}
    # VALID_DATA already has obfuscation_latency_sec, so both are present.
    with pytest.raises(ValidationError, match="one unit only"):
        Benchmark(**data)


def test_reject_missing_latency():
    data = {**VALID_DATA}
    del data["obfuscation_latency_sec"]
    with pytest.raises(ValidationError, match="[Rr]equired"):
        Benchmark(**data)


def test_reject_negative_latency_minutes():
    data = {**VALID_DATA}
    del data["obfuscation_latency_sec"]
    data["obfuscation_latency_min"] = -1.0
    with pytest.raises(ValidationError, match="non-negative"):
        Benchmark(**data)


def test_loader_accepts_latency_minutes_key(tmp_path):
    from sitegen.load import load_benchmarks

    import yaml

    data = {**VALID_DATA}
    del data["obfuscation_latency_sec"]
    data["obfuscation_latency_min"] = 9.0
    (tmp_path / "a.yaml").write_text(yaml.dump(data))
    benchmarks = load_benchmarks(tmp_path)
    assert benchmarks[0].obfuscation_latency_min == 9.0


def test_loader_accepts_we_latency_minutes_key(tmp_path):
    from sitegen.load import load_benchmarks

    import yaml

    data = _we_data()
    del data["encryption_latency_sec"]
    data["encryption_latency_min"] = 12.0
    (tmp_path / "we.yaml").write_text(yaml.dump(data))
    benchmarks = load_benchmarks(
        tmp_path,
        allowed_targets=["witness-encryption-64"],
        default_target="witness-encryption-64",
        target_labels={"witness-encryption-64": WE_LABELS},
    )
    assert benchmarks[0].obfuscation_latency_min == 12.0


def test_accept_breakdowns():
    data = {
        **VALID_DATA,
        "obfuscation_time_breakdown": [
            {"step": "Sampling", "time_hours": 0.6},
            {"step": "Encoding", "time_hours": 0.3},
        ],
        "obfuscation_size_breakdown": [
            {"component": "Matrices", "size_gb": 200.0},
        ],
    }
    bm = Benchmark(**data)
    assert len(bm.obfuscation_time_breakdown) == 2
    assert bm.obfuscation_time_breakdown[0].step == "Sampling"
    assert bm.obfuscation_size_breakdown[0].size_gb == 200.0
    assert bm.evaluation_time_breakdown is None


def test_breakdowns_default_to_none():
    bm = Benchmark(**VALID_DATA)
    assert bm.obfuscation_time_breakdown is None
    assert bm.evaluation_time_breakdown is None
    assert bm.obfuscation_size_breakdown is None


def test_reject_breakdown_sum_exceeds_total():
    # obfuscation_total_time_hours is 1.0; sub-steps sum to 1.5.
    data = {
        **VALID_DATA,
        "obfuscation_time_breakdown": [
            {"step": "A", "time_hours": 1.0},
            {"step": "B", "time_hours": 0.5},
        ],
    }
    with pytest.raises(ValidationError, match="exceeds the phase total"):
        Benchmark(**data)


def test_reject_size_breakdown_sum_exceeds_total():
    # storage_gb is 256.0; components sum to 300.0.
    data = {
        **VALID_DATA,
        "obfuscation_size_breakdown": [
            {"component": "X", "size_gb": 300.0},
        ],
    }
    with pytest.raises(ValidationError, match="exceeds the phase total"):
        Benchmark(**data)


def test_breakdown_sum_equal_to_total_ok():
    data = {
        **VALID_DATA,
        "obfuscation_time_breakdown": [
            {"step": "A", "time_hours": 0.7},
            {"step": "B", "time_hours": 0.3},
        ],
    }
    bm = Benchmark(**data)
    assert sum(i.time_hours for i in bm.obfuscation_time_breakdown) == 1.0


def test_reject_negative_breakdown_value():
    data = {
        **VALID_DATA,
        "obfuscation_time_breakdown": [{"step": "A", "time_hours": -1.0}],
    }
    with pytest.raises(ValidationError, match="non-negative"):
        Benchmark(**data)


def test_reject_empty_breakdown_label():
    data = {
        **VALID_DATA,
        "obfuscation_time_breakdown": [{"step": "  ", "time_hours": 1.0}],
    }
    with pytest.raises(ValidationError, match="non-empty"):
        Benchmark(**data)


def test_reject_unknown_breakdown_item_field():
    data = {
        **VALID_DATA,
        "obfuscation_time_breakdown": [
            {"step": "A", "time_hours": 0.5, "bogus": 1}
        ],
    }
    with pytest.raises(ValidationError, match="extra"):
        Benchmark(**data)


def test_loader_translates_target_specific_breakdown_keys(tmp_path):
    """WE breakdown keys translate to canonical breakdown fields."""
    from sitegen.load import load_benchmarks

    import yaml

    data = _we_data()
    data["encryption_time_breakdown"] = [{"step": "Sampling", "time_hours": 0.5}]
    (tmp_path / "we.yaml").write_text(yaml.dump(data))
    benchmarks = load_benchmarks(
        tmp_path,
        allowed_targets=["witness-encryption-64"],
        default_target="witness-encryption-64",
        target_labels={"witness-encryption-64": WE_LABELS},
    )
    bm = benchmarks[0]
    assert bm.obfuscation_time_breakdown[0].step == "Sampling"


def test_loader_rejects_wrong_target_breakdown_key(tmp_path):
    """Using the canonical obfuscation breakdown key is rejected for WE."""
    from sitegen.load import load_benchmarks

    import yaml

    data = _we_data()
    data["obfuscation_time_breakdown"] = [{"step": "Sampling", "time_hours": 0.5}]
    (tmp_path / "bad.yaml").write_text(yaml.dump(data))
    with pytest.raises(SystemExit):
        load_benchmarks(
            tmp_path,
            allowed_targets=["witness-encryption-64"],
            default_target="witness-encryption-64",
            target_labels={"witness-encryption-64": WE_LABELS},
        )


def test_loader_rejects_unknown_target(tmp_path):
    from sitegen.load import load_benchmarks

    import yaml

    (tmp_path / "a.yaml").write_text(
        yaml.dump({**VALID_DATA, "target": "no-such-target"})
    )
    with pytest.raises(SystemExit):
        load_benchmarks(
            tmp_path,
            allowed_targets=["obfuscated-prf-110"],
            default_target="obfuscated-prf-110",
        )
