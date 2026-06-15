"""GPU hourly-price lookup used to derive benchmark cost.

Cost is never stored in benchmark YAML; it is computed as
``hourly_price * total_time_hours``.

Each benchmark's ``device`` field is a short GPU id (e.g. ``H200``). A registry
(``config/gpu_devices.yaml``) maps each id to a RunPod GPU type id. At build time
the live RunPod GraphQL API is queried for current prices. There is no committed
fallback price: if the live price cannot be fetched, the id resolves to no price
and cost is rendered as ND.
"""

from __future__ import annotations

import json
import os
import urllib.request
from pathlib import Path

import yaml

RUNPOD_GRAPHQL_URL = "https://api.runpod.io/graphql"
_GPU_TYPES_QUERY = (
    "query GpuTypes { gpuTypes { id displayName securePrice communityPrice } }"
)
GPU_REGISTRY_FILE = "config/gpu_devices.yaml"


def normalize_key(name: str) -> str:
    """Normalize a GPU id or name for case/space-insensitive matching."""
    return " ".join(str(name).lower().split())


def _price_from_gpu_type(gpu: dict) -> float | None:
    """Use the community-cloud price, falling back to secure if unavailable."""
    for key in ("communityPrice", "securePrice"):
        value = gpu.get(key)
        if isinstance(value, (int, float)) and value > 0:
            return float(value)
    return None


def fetch_runpod_prices(timeout: float = 10.0) -> dict[str, float]:
    """Query RunPod for GPU hourly prices, keyed by normalized GPU type name.

    Returns an empty dict on any failure (network, auth, schema change).
    """
    url = RUNPOD_GRAPHQL_URL
    api_key = os.environ.get("RUNPOD_API_KEY")
    if api_key:
        url = f"{url}?api_key={api_key}"

    body = json.dumps({"query": _GPU_TYPES_QUERY}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            # RunPod's edge rejects the default Python-urllib UA with 403.
            "User-Agent": "obfusbench-sitegen/1.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except Exception:
        return {}

    gpu_types = (payload.get("data") or {}).get("gpuTypes")
    if not isinstance(gpu_types, list):
        return {}

    prices: dict[str, float] = {}
    for gpu in gpu_types:
        if not isinstance(gpu, dict):
            continue
        price = _price_from_gpu_type(gpu)
        if price is None:
            continue
        for field in ("id", "displayName"):
            name = gpu.get(field)
            if isinstance(name, str) and name.strip():
                prices[normalize_key(name)] = price
    return prices


def load_gpu_registry(project_root: Path) -> dict[str, dict]:
    """Load the GPU registry, keyed by normalized short GPU id.

    Each value is ``{"runpod_name": <RunPod GPU type id>, "display": <name>}``.
    ``display`` is the canonical name shown in the UI; it falls back to
    ``runpod_name`` when not given.
    """
    path = project_root / GPU_REGISTRY_FILE
    if not path.is_file():
        return {}
    try:
        raw = yaml.safe_load(path.read_text()) or {}
    except (yaml.YAMLError, OSError):
        return {}
    if not isinstance(raw, dict):
        return {}

    registry: dict[str, dict] = {}
    for gid, entry in raw.items():
        if not isinstance(entry, dict):
            continue
        runpod_name = str(entry.get("runpod_name", "")).strip()
        if not runpod_name:
            continue
        display = str(entry.get("display", "")).strip() or runpod_name
        registry[normalize_key(gid)] = {"runpod_name": runpod_name, "display": display}
    return registry


def device_display(registry: dict[str, dict], device: str | None) -> str | None:
    """Normalized display name for a device id (never the raw YAML token).

    Returns None when no device is set; falls back to the raw value only for an
    id that is absent from the registry (so it is still visible).
    """
    if not device:
        return None
    entry = registry.get(normalize_key(device))
    if entry:
        return entry["display"]
    return device


def resolve_prices(project_root: Path, *, fetch: bool = True) -> tuple[dict[str, float], str]:
    """Resolve a map of normalized GPU id -> USD/hour from live RunPod prices.

    There is no fallback: if the live fetch fails (or ``fetch`` is False), the
    returned map is empty and callers should render cost as ND. Returns
    ``(price_map, source_label)``.
    """
    registry = load_gpu_registry(project_root)
    live = fetch_runpod_prices() if fetch else {}

    if not live:
        return {}, "none (live fetch unavailable)" if fetch else "none (fetch disabled)"

    prices: dict[str, float] = {}
    for gid, entry in registry.items():
        price = live.get(normalize_key(entry["runpod_name"]))
        if price is not None:
            prices[gid] = price
    return prices, "RunPod API"


def price_for_device(prices: dict[str, float], device: str | None) -> float | None:
    """Look up the hourly price for a short GPU id, or None if unknown."""
    if not device:
        return None
    return prices.get(normalize_key(device))
