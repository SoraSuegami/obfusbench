"""Pydantic models for benchmark entries."""

from __future__ import annotations

import math
import re
from typing import Annotated

from pydantic import BaseModel, Field, HttpUrl, field_validator, model_validator


def slugify(text: str) -> str:
    """Derive a URL-safe slug from a display name."""
    s = text.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_-]+", "-", s)
    return s.strip("-")


def _check_finite_nonneg(v: float, field_name: str) -> float:
    if not math.isfinite(v):
        raise ValueError(f"{field_name} must be finite")
    if v < 0:
        raise ValueError(f"{field_name} must be non-negative")
    return v


class Benchmark(BaseModel):
    """A single iO implementation benchmark entry."""

    model_config = {"extra": "forbid"}

    id: str
    authors: str | list[str]
    url: Annotated[str, Field(default=None)]  # optional
    commit: str | None = None

    obfuscation_latency_sec: float
    obfuscation_cost_usd: float
    obfuscation_peak_memory_gb: float
    obfuscated_circuit_size_gb: float
    evaluation_latency_sec: float
    evaluation_cost_usd: float
    evaluation_peak_memory_gb: float

    # Set after validation
    slug: str = ""

    @field_validator("id")
    @classmethod
    def id_must_be_nonempty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("id must be a non-empty string")
        return v

    @field_validator("authors", mode="before")
    @classmethod
    def normalize_authors(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            return [v]
        return v

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
        "obfuscation_cost_usd",
        "obfuscation_peak_memory_gb",
        "obfuscated_circuit_size_gb",
        "evaluation_latency_sec",
        "evaluation_cost_usd",
        "evaluation_peak_memory_gb",
    )
    @classmethod
    def check_metric(cls, v: float, info) -> float:
        return _check_finite_nonneg(v, info.field_name)

    @model_validator(mode="after")
    def set_slug(self) -> "Benchmark":
        self.slug = slugify(self.id)
        return self


# Metric fields for iteration
METRIC_FIELDS: list[dict[str, str]] = [
    {"key": "obfuscation_latency_sec", "label": "Obf. latency", "unit": "sec"},
    {"key": "obfuscation_cost_usd", "label": "Obf. cost", "unit": "$"},
    {"key": "obfuscation_peak_memory_gb", "label": "Obf. peak mem", "unit": "GB"},
    {"key": "obfuscated_circuit_size_gb", "label": "Circuit size", "unit": "GB"},
    {"key": "evaluation_latency_sec", "label": "Eval. latency", "unit": "sec"},
    {"key": "evaluation_cost_usd", "label": "Eval. cost", "unit": "$"},
    {"key": "evaluation_peak_memory_gb", "label": "Eval. peak mem", "unit": "GB"},
]


def generate_json_schema() -> dict:
    """Generate JSON Schema from the Pydantic model, excluding internal fields."""
    schema = Benchmark.model_json_schema()
    # Remove the slug field since it's derived
    if "properties" in schema and "slug" in schema["properties"]:
        del schema["properties"]["slug"]
    if "required" in schema and "slug" in schema["required"]:
        schema["required"].remove("slug")
    return schema
