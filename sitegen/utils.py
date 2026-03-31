"""Utility helpers for the site generator."""

from __future__ import annotations

import re


def format_number(value: float) -> str:
    """Format a number for display: trimmed fixed-point or scientific notation."""
    if value == 0:
        return "0"
    abs_val = abs(value)
    if abs_val >= 1e6 or abs_val < 0.001:
        return f"{value:.2e}"
    if value == int(value):
        return str(int(value))
    # Up to 4 decimal places, trimmed
    formatted = f"{value:.4f}".rstrip("0").rstrip(".")
    return formatted


def commit_url(repo_url: str | None, commit: str | None) -> str | None:
    """Build a GitHub commit URL if both repo_url and commit look right."""
    if not repo_url or not commit:
        return None
    # Check it looks like a GitHub repo URL
    if not re.match(r"https://github\.com/[\w.-]+/[\w.-]+", repo_url):
        return None
    # Check commit looks like a hex hash (at least 7 chars)
    if not re.match(r"^[0-9a-fA-F]{7,40}$", commit):
        return None
    clean_url = repo_url.rstrip("/")
    return f"{clean_url}/commit/{commit}"
