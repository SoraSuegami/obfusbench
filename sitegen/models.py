"""Pydantic models for benchmark entries."""

from __future__ import annotations

import datetime
import math
import re
import unicodedata

from pydantic import BaseModel, Field, HttpUrl, field_validator, model_validator


def slugify(text: str) -> str:
    """Derive an ASCII URL-safe slug from a display name."""
    s = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    s = s.lower().strip()
    s = re.sub(r"[^a-z0-9\s_-]", "", s)
    s = re.sub(r"[\s_-]+", "-", s)
    return s.strip("-")


def _check_finite_nonneg(v: float, field_name: str) -> float:
    if not math.isfinite(v):
        raise ValueError(f"{field_name} must be finite")
    if v < 0:
        raise ValueError(f"{field_name} must be non-negative")
    return v


def _check_optional_finite_nonneg(v: float | None, field_name: str) -> float | None:
    if v is None:
        return None
    return _check_finite_nonneg(v, field_name)


class Benchmark(BaseModel):
    """A single iO implementation benchmark entry."""

    model_config = {"extra": "forbid"}

    id: str
    authors: str | list[str]
    developers: str | list[str]
    url: str | None = Field(default=None)
    commit: str | None = None
    date: datetime.date
    target: str | None = Field(
        default=None,
        description=(
            "Benchmark target id (see targets in config/site.yaml). "
            "Defaults to the first configured target when omitted."
        ),
    )
    device: str | None = Field(
        default=None,
        description=(
            "Short GPU id the benchmark ran on (see config/gpu_devices.yaml), "
            "e.g. 'H100', 'H200', 'A100'. Used to look up the hourly price so "
            "cost can be derived as price x total time."
        ),
    )

    obfuscation_latency_sec: float
    obfuscation_total_time_hours: float
    obfuscation_peak_memory_gb: float | None = None
    storage_gb: float
    evaluation_latency_sec: float
    evaluation_total_time_hours: float
    evaluation_peak_memory_gb: float | None = None

    # Set after validation
    slug: str = ""

    @field_validator("id")
    @classmethod
    def id_must_be_nonempty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("id must be a non-empty string")
        return v.strip()

    @field_validator("authors", "developers", mode="before")
    @classmethod
    def normalize_people(cls, v: str | list[str], info) -> list[str]:
        if isinstance(v, str):
            values = [v]
        elif isinstance(v, list):
            values = v
        else:
            return v

        names: list[str] = []
        for item in values:
            if not isinstance(item, str):
                raise ValueError(f"{info.field_name} must contain strings")
            name = item.strip()
            if not name:
                raise ValueError(f"{info.field_name} must contain non-empty names")
            names.append(name)

        if not names:
            raise ValueError(f"{info.field_name} must contain at least one name")
        return names

    @field_validator("url", mode="before")
    @classmethod
    def validate_url(cls, v: str | None) -> str | None:
        if v is None:
            return None
        if not isinstance(v, str):
            raise ValueError("url must be a string")
        if not v.startswith(("http://", "https://")):
            raise ValueError("url must be an http or https URL")
        # Let pydantic's HttpUrl do the heavy lifting
        HttpUrl(v)
        return v

    @field_validator("target", mode="before")
    @classmethod
    def normalize_target(cls, v: str | None) -> str | None:
        if v is None:
            return None
        if not isinstance(v, str) or not v.strip():
            raise ValueError("target must be a non-empty string")
        return v.strip()

    @field_validator("device", mode="before")
    @classmethod
    def normalize_device(cls, v: str | None) -> str | None:
        if v is None:
            return None
        if not isinstance(v, str) or not v.strip():
            raise ValueError("device must be a non-empty string")
        return v.strip()

    @field_validator("commit", mode="before")
    @classmethod
    def normalize_commit(cls, v: str | None) -> str | None:
        if v is None:
            return None
        if isinstance(v, str) and v.strip() == "":
            return None
        return v

    @field_validator(
        "obfuscation_latency_sec",
        "obfuscation_total_time_hours",
        "storage_gb",
        "evaluation_latency_sec",
        "evaluation_total_time_hours",
    )
    @classmethod
    def check_metric(cls, v: float, info) -> float:
        return _check_finite_nonneg(v, info.field_name)

    @field_validator(
        "obfuscation_peak_memory_gb",
        "evaluation_peak_memory_gb",
    )
    @classmethod
    def check_optional_metric(cls, v: float | None, info) -> float | None:
        return _check_optional_finite_nonneg(v, info.field_name)

    @model_validator(mode="after")
    def set_slug(self) -> "Benchmark":
        if not re.search(r"[A-Za-z0-9]", self.id):
            raise ValueError("id must contain at least one URL-safe ASCII letter or digit")
        self.slug = slugify(self.id)
        if not self.slug:
            raise ValueError("id must contain at least one URL-safe character")
        return self


# Default labels (obfuscation terminology). A target in config/site.yaml may
# override any of these to rename the two phases / the size metric. The *_key
# entries are the YAML field-name tokens for that target; the *_short/_full/size
# entries are display text. Internally the model always uses the canonical
# (obfuscation) field names — the loader translates a target's keys to canonical.
DEFAULT_LABELS: dict[str, str] = {
    "phase1_short": "Obf.",
    "phase1_full": "Obfuscation",
    "phase1_key": "obfuscation",
    "phase2_short": "Eval.",
    "phase2_full": "Evaluation",
    "phase2_key": "evaluation",
    "size": "Obfuscation size",
    "size_key": "storage_gb",
}

# Canonical (internal) metric field names on the Benchmark model.
CANONICAL_METRIC_KEYS: tuple[str, ...] = (
    "obfuscation_latency_sec",
    "obfuscation_total_time_hours",
    "obfuscation_peak_memory_gb",
    "storage_gb",
    "evaluation_latency_sec",
    "evaluation_total_time_hours",
    "evaluation_peak_memory_gb",
)


def yaml_key_map(labels: dict[str, str] | None = None) -> dict[str, str]:
    """Map a target's YAML metric key -> canonical model field name.

    For the default (obfuscation) labels this is the identity map.
    """
    lbl = {**DEFAULT_LABELS, **(labels or {})}
    p1, p2, size = lbl["phase1_key"], lbl["phase2_key"], lbl["size_key"]
    return {
        f"{p1}_latency_sec": "obfuscation_latency_sec",
        f"{p1}_total_time_hours": "obfuscation_total_time_hours",
        f"{p1}_peak_memory_gb": "obfuscation_peak_memory_gb",
        size: "storage_gb",
        f"{p2}_latency_sec": "evaluation_latency_sec",
        f"{p2}_total_time_hours": "evaluation_total_time_hours",
        f"{p2}_peak_memory_gb": "evaluation_peak_memory_gb",
    }


def metric_fields(labels: dict[str, str] | None = None) -> list[dict[str, str]]:
    """Leaderboard table columns, in display order, labeled per target.

    This is the table layout only; it does not include every numeric field
    (see NUMERIC_METRIC_KEYS for schema constraints).
    """
    lbl = {**DEFAULT_LABELS, **(labels or {})}
    return [
        {"key": "obfuscation_total_time_hours", "label": f"{lbl['phase1_short']} total time", "unit": "h"},
        {"key": "evaluation_total_time_hours", "label": f"{lbl['phase2_short']} total time", "unit": "h"},
        {"key": "storage_gb", "label": lbl["size"], "unit": "GB"},
        {"key": "obfuscation_latency_sec", "label": f"{lbl['phase1_short']} latency", "unit": "sec"},
        {"key": "evaluation_latency_sec", "label": f"{lbl['phase2_short']} latency", "unit": "sec"},
    ]

# All numeric metric fields on the model (independent of table display), used to
# apply the non-negative (minimum: 0) constraint in the generated JSON Schema.
NUMERIC_METRIC_KEYS: tuple[str, ...] = (
    "obfuscation_latency_sec",
    "obfuscation_total_time_hours",
    "obfuscation_peak_memory_gb",
    "storage_gb",
    "evaluation_latency_sec",
    "evaluation_total_time_hours",
    "evaluation_peak_memory_gb",
)


def generate_json_schema() -> dict:
    """Generate JSON Schema from the Pydantic model, excluding internal fields."""
    schema = Benchmark.model_json_schema()
    properties = schema.get("properties", {})

    # Remove the slug field since it's derived.
    properties.pop("slug", None)
    if "required" in schema and "slug" in schema["required"]:
        schema["required"].remove("slug")

    # Mirror runtime validation closely enough for schema-first contributors.
    if "id" in properties:
        properties["id"].update({"minLength": 1, "pattern": r".*[A-Za-z0-9].*"})

    for key in ("authors", "developers"):
        prop = properties.get(key, {})
        for branch in prop.get("anyOf", []):
            if branch.get("type") == "string":
                branch.update({"minLength": 1, "pattern": r".*\S.*"})
            elif branch.get("type") == "array":
                branch["minItems"] = 1
                branch.setdefault("items", {}).update({"minLength": 1, "pattern": r".*\S.*"})

    url_prop = properties.get("url", {})
    for branch in url_prop.get("anyOf", []):
        if branch.get("type") == "string":
            branch.update({"format": "uri", "pattern": r"^https?://[^\s/]+(?:/[^\s]*)?$"})

    for key in ("target", "device"):
        prop = properties.get(key, {})
        for branch in prop.get("anyOf", []):
            if branch.get("type") == "string":
                branch.update({"minLength": 1, "pattern": r".*\S.*"})

    for key in NUMERIC_METRIC_KEYS:
        prop = properties.get(key, {})
        if prop.get("type") == "number":
            prop["minimum"] = 0
        for branch in prop.get("anyOf", []):
            if branch.get("type") == "number":
                branch["minimum"] = 0

    return schema
