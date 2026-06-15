"""Tests for GPU price resolution and cost derivation."""

from pathlib import Path

import yaml

from sitegen.pricing import (
    load_gpu_registry,
    normalize_key,
    price_for_device,
    resolve_prices,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def test_normalize_key_is_case_and_space_insensitive():
    assert normalize_key("  H200 ") == "h200"
    assert normalize_key("NVIDIA  H100   80GB") == "nvidia h100 80gb"


def test_registry_maps_short_ids_to_runpod_names():
    registry = load_gpu_registry(PROJECT_ROOT)
    assert registry["h100"]["runpod_name"] == "NVIDIA H100 80GB HBM3"
    assert registry["h200"]["runpod_name"] == "NVIDIA H200"
    # display defaults to a normalized name, not the raw id.
    assert registry["h200"]["display"] == "H200 SXM"


def test_device_display_normalizes_id():
    from sitegen.pricing import device_display

    registry = load_gpu_registry(PROJECT_ROOT)
    assert device_display(registry, "H200") == "H200 SXM"
    assert device_display(registry, "rtxpro6000") == "RTX PRO 6000"
    assert device_display(registry, None) is None
    # Unknown id falls back to the raw value so it stays visible.
    assert device_display(registry, "mystery-gpu") == "mystery-gpu"


def test_offline_resolve_yields_no_prices():
    """With no live fetch there is no fallback, so prices are empty (-> ND)."""
    prices, source = resolve_prices(PROJECT_ROOT, fetch=False)
    assert prices == {}
    assert "fetch disabled" in source
    assert price_for_device(prices, "H100") is None


def test_failed_fetch_yields_no_prices(monkeypatch):
    """A failed live fetch resolves to no prices (cost becomes ND)."""
    monkeypatch.setattr("sitegen.pricing.fetch_runpod_prices", lambda *a, **k: {})
    prices, source = resolve_prices(PROJECT_ROOT, fetch=True)
    assert prices == {}
    assert "unavailable" in source
    assert price_for_device(prices, "H200") is None


def test_resolve_prices_uses_live_runpod_prices(tmp_path, monkeypatch):
    """Live RunPod prices resolve per short id via the registry mapping."""
    registry_dir = tmp_path / "config"
    registry_dir.mkdir()
    (registry_dir / "gpu_devices.yaml").write_text(
        yaml.dump({"H100": {"runpod_name": "NVIDIA H100 80GB HBM3"}})
    )

    monkeypatch.setattr(
        "sitegen.pricing.fetch_runpod_prices",
        lambda *a, **k: {normalize_key("NVIDIA H100 80GB HBM3"): 3.29},
    )

    prices, source = resolve_prices(tmp_path, fetch=True)
    assert source == "RunPod API"
    assert price_for_device(prices, "H100") == 3.29
    assert price_for_device(prices, "h100") == 3.29
    assert price_for_device(prices, None) is None
    assert price_for_device(prices, "no-such-gpu") is None
