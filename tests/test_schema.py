"""Tests for the generated benchmark JSON Schema."""

import pytest
from jsonschema import Draft202012Validator, FormatChecker

from sitegen.models import generate_json_schema
from tests.test_validation import VALID_DATA


def validate_schema(data):
    validator = Draft202012Validator(
        generate_json_schema(), format_checker=FormatChecker()
    )
    errors = sorted(validator.iter_errors(data), key=lambda e: e.path)
    return errors


def test_schema_accepts_valid_data():
    assert validate_schema(VALID_DATA) == []


@pytest.mark.parametrize(
    "patch",
    [
        {"id": "   "},
        {"id": "!!!"},
        {"authors": ""},
        {"authors": []},
        {"authors": ["Alice", ""]},
        {"developers": []},
        {"implementation_url": "ftp://example.com/repo"},
        {"implementation_url": "http://"},
        {"paper_url": "ftp://example.com/paper"},
        {"obfuscation_latency_sec": -1},
        {"obfuscation_peak_memory_gb": -1},
    ],
)
def test_schema_rejects_runtime_invalid_data(patch):
    data = {**VALID_DATA, **patch}
    assert validate_schema(data)


def test_schema_accepts_explicit_null_url_and_memory():
    data = {
        **VALID_DATA,
        "paper_url": None,
        "implementation_url": None,
        "obfuscation_peak_memory_gb": None,
        "evaluation_peak_memory_gb": None,
    }
    assert validate_schema(data) == []


def test_schema_excludes_internal_slug():
    schema = generate_json_schema()
    assert "slug" not in schema["properties"]
