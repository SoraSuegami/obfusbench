"""Utility helpers for the site generator."""

from __future__ import annotations

import re


def format_number(value: float | None) -> str:
    """Format a number for display, using ND for unavailable values."""
    if value is None:
        return "ND"
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


def format_sci(value: float | None) -> str:
    """Format a number in scientific notation (3 significant digits, e.g. 5.94e+05).

    Used for the leaderboard table so every numeric cell shares one format.
    Unavailable values render as ND.
    """
    if value is None:
        return "ND"
    return f"{value:.2e}"


_NUMERIC_LITERAL_RE = re.compile(r"^[+-]?([0-9]*\.?[0-9]+)(?:[eE][+-]?[0-9]+)?$")


def significant_digits(literal) -> int | None:
    """Count significant digits in a numeric literal string (e.g. '6.695e46' -> 4).

    Counts the source literal a contributor wrote, since the parsed float no
    longer carries that information. Leading zeros are not significant; written
    trailing zeros are (so '512.0' is 4). Returns 1 for a zero literal, and None
    when the token is not a plain number.
    """
    if literal is None:
        return None
    m = _NUMERIC_LITERAL_RE.match(str(literal).strip())
    if not m:
        return None
    mantissa = m.group(1).replace(".", "").lstrip("0")
    return len(mantissa) if mantissa else 1


def format_sci_p(value: float | None, sigfigs: int | None = None) -> str:
    """Scientific notation with ``max(3, sigfigs)`` significant digits.

    ``sigfigs`` is the precision implied by the source literal (see
    :func:`significant_digits`): values written with more than 3 significant
    digits keep them, while 3-or-fewer digit values are shown at 3. Unavailable
    values render as ND.
    """
    if value is None:
        return "ND"
    n = sigfigs if isinstance(sigfigs, int) and sigfigs >= 3 else 3
    return f"{value:.{n - 1}e}"


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
