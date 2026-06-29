"""Tests for significant-digit detection and precision-aware formatting."""

from pathlib import Path

import yaml

from sitegen.load import load_benchmarks
from sitegen.utils import format_sci_p, significant_digits

from tests.test_validation import VALID_DATA


def test_significant_digits_counts_literal():
    assert significant_digits("7.74e46") == 3
    assert significant_digits("6.695e46") == 4
    assert significant_digits("1.2e46") == 2
    assert significant_digits("512.0") == 4   # written trailing zero is significant
    assert significant_digits("0.007") == 1   # leading zeros are not
    assert significant_digits("100") == 3
    assert significant_digits("1e46") == 1
    assert significant_digits("0") == 1


def test_significant_digits_non_numeric():
    assert significant_digits("abc") is None
    assert significant_digits(None) is None


def test_format_sci_p_floors_at_three():
    # Fewer than 3 significant figures still render at 3.
    assert format_sci_p(1.2e46, 2) == "1.20e+46"
    assert format_sci_p(1.2e46, None) == "1.20e+46"
    assert format_sci_p(7.74e46, 3) == "7.74e+46"


def test_format_sci_p_matches_higher_precision():
    assert format_sci_p(6.695e46, 4) == "6.695e+46"
    assert format_sci_p(1.23456e3, 6) == "1.23456e+03"


def test_format_sci_p_none_is_nd():
    assert format_sci_p(None, 4) == "ND"


def test_loader_records_display_sigfigs(tmp_path):
    data = {
        **VALID_DATA,
        # 4-sig-fig literals as strings (PyYAML keeps sci notation as text).
        "obfuscation_total_time_hours": 1.234e46,
        "storage_gb": 5.6e2,
    }
    # Write with explicit 4- and 2-sig-fig literals to exercise the counter.
    text = yaml.dump(data)
    # Force specific literal forms for the two fields under test.
    text += "\nobfuscation_total_time_hours: 1.234e46\nstorage_gb: 5.6e2\n"
    (tmp_path / "a.yaml").write_text(text)

    benchmarks = load_benchmarks(tmp_path)
    sf = benchmarks[0].display_sigfigs
    assert sf["obfuscation_total_time_hours"] == 4
    assert sf["storage_gb"] == 2


def test_loader_latency_sigfigs_from_seconds_literal(tmp_path):
    data = {**VALID_DATA}
    # 3-sig-fig seconds literal; precision should attach to the minutes field.
    data["obfuscation_latency_sec"] = 5.94e5
    (tmp_path / "a.yaml").write_text(
        yaml.dump({k: v for k, v in data.items() if k != "obfuscation_latency_sec"})
        + "\nobfuscation_latency_sec: 5.94e5\n"
    )
    benchmarks = load_benchmarks(tmp_path)
    assert benchmarks[0].display_sigfigs["obfuscation_latency_min"] == 3


def test_loader_breakdown_sigfigs_per_item(tmp_path):
    data = {**VALID_DATA}
    text = yaml.dump(data) + (
        "\nobfuscation_time_breakdown:\n"
        "  - step: A\n"
        "    time_hours: 1.2345e-1\n"   # 5 sig figs, < total (1.0)
        "  - step: B\n"
        "    time_hours: 1.0e-1\n"      # 2 sig figs
    )
    (tmp_path / "a.yaml").write_text(text)
    benchmarks = load_benchmarks(tmp_path)
    assert benchmarks[0].display_sigfigs["obfuscation_time_breakdown"] == [5, 2]
