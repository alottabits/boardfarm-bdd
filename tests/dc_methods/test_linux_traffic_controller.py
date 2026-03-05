"""Pytest validation for LinuxTrafficController via boardfarm fixtures.

Validates all TrafficController template methods implemented by LinuxTrafficController.
Uses boardfarm device_manager/devices fixtures — requires full boardfarm args.

Tests are ordered so that each one leaves the device in a known (pristine) state for
the next.  The ``tc`` fixture auto-clears impairment after every test via a
``yield``-based teardown.

Run from boardfarm-bdd/ with venv activated and wan1-tc container running:

    pytest tests/dc_methods/test_linux_traffic_controller.py -v \\
        --board-name sdwan \\
        --env-config bf_config/bf_env_sdwan.json \\
        --inventory-config bf_config/bf_config_sdwan.json \\
        --legacy --skip-boot --save-console-logs ""

By default, tests target ``wan1_tc``.  Set the ``TC_DEVICE_NAME`` env variable to
target a different device, e.g. ``TC_DEVICE_NAME=wan2_tc``.

Prerequisites:
- Traffic controller container(s) running (``docker compose -p boardfarm-bdd-sdwan ... up``)
- Python venv with boardfarm3 installed (``.venv-3.12``)
- Raikou has injected eth-north and eth-dut into the TC containers
"""

from __future__ import annotations

import os
import time
from typing import cast

import pytest

from boardfarm3.lib.traffic_control import ImpairmentProfile, profile_from_dict
from boardfarm3.templates.traffic_controller import TrafficController

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_TC_DEVICE_NAME: str = os.environ.get("TC_DEVICE_NAME", "wan1_tc")

# Interface names as defined in bf_env_sdwan.json
_IFACE_NORTH = "eth-north"
_IFACE_DUT = "eth-dut"

# Tolerance for round-trip verification: tc netem silently clamps/rounds values.
_LATENCY_TOL_MS = 1
_LOSS_TOL_PCT = 0.01
_BW_TOL_MBPS = 5  # TBF rate rounding


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _require_tc(devices: object, name: str) -> TrafficController:
    """Return the TC device or skip if unavailable."""
    dev = getattr(devices, name, None)
    if dev is None:
        pytest.skip(
            f"TC device {name!r} not in testbed "
            "(use --board-name sdwan and ensure the container is running)"
        )
    return cast(TrafficController, dev)


@pytest.fixture()
def tc(devices: object) -> TrafficController:  # type: ignore[name-defined]
    """Yield the TrafficController device; clear impairment after each test."""
    device = _require_tc(devices, _TC_DEVICE_NAME)
    yield device
    try:
        device.clear()
    except Exception:  # noqa: BLE001
        pass  # Best-effort teardown; do not mask test failures


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _assert_profile_approx(
    actual: ImpairmentProfile,
    expected: ImpairmentProfile,
    *,
    check_bandwidth: bool = True,
    label: str = "",
) -> None:
    """Assert that *actual* matches *expected* within acceptable tolerances."""
    prefix = f"[{label}] " if label else ""
    assert abs(actual.latency_ms - expected.latency_ms) <= _LATENCY_TOL_MS, (
        f"{prefix}latency_ms: expected {expected.latency_ms}, got {actual.latency_ms}"
    )
    assert abs(actual.jitter_ms - expected.jitter_ms) <= _LATENCY_TOL_MS, (
        f"{prefix}jitter_ms: expected {expected.jitter_ms}, got {actual.jitter_ms}"
    )
    assert abs(actual.loss_percent - expected.loss_percent) <= _LOSS_TOL_PCT, (
        f"{prefix}loss_percent: expected {expected.loss_percent}, got {actual.loss_percent}"
    )
    if check_bandwidth:
        if expected.bandwidth_limit_mbps is None:
            assert actual.bandwidth_limit_mbps is None, (
                f"{prefix}bandwidth_limit_mbps: expected None, got {actual.bandwidth_limit_mbps}"
            )
        else:
            assert actual.bandwidth_limit_mbps is not None, (
                f"{prefix}bandwidth_limit_mbps: expected non-None, got None"
            )
            assert (
                abs(actual.bandwidth_limit_mbps - expected.bandwidth_limit_mbps) <= _BW_TOL_MBPS
            ), (
                f"{prefix}bandwidth_limit_mbps: expected {expected.bandwidth_limit_mbps}, "
                f"got {actual.bandwidth_limit_mbps}"
            )


# ---------------------------------------------------------------------------
# Tests: get_interface_profiles (read-only, all interfaces)
# ---------------------------------------------------------------------------


def test_get_interface_profiles_returns_dict(tc: TrafficController) -> None:
    """get_interface_profiles() returns a dict keyed by interface name."""
    profiles = tc.get_interface_profiles()

    assert isinstance(profiles, dict), f"Expected dict, got {type(profiles)}"
    assert len(profiles) > 0, "Expected at least one interface"
    for iface, profile in profiles.items():
        assert isinstance(iface, str), f"Expected str key, got {type(iface)}"
        assert isinstance(profile, ImpairmentProfile), (
            f"Expected ImpairmentProfile for {iface!r}, got {type(profile)}"
        )
    print(f"✓ get_interface_profiles: {list(profiles.keys())}")


def test_get_interface_profiles_after_clear(tc: TrafficController) -> None:
    """After clear(), get_interface_profiles() returns zero-impairment profiles for all ifaces."""
    tc.clear()
    profiles = tc.get_interface_profiles()

    for iface, profile in profiles.items():
        assert profile.latency_ms == 0, (
            f"[{iface}] Expected latency_ms=0 after clear, got {profile.latency_ms}"
        )
        assert profile.jitter_ms == 0, (
            f"[{iface}] Expected jitter_ms=0 after clear, got {profile.jitter_ms}"
        )
        assert profile.loss_percent == 0.0, (
            f"[{iface}] Expected loss_percent=0 after clear, got {profile.loss_percent}"
        )
        assert profile.bandwidth_limit_mbps is None, (
            f"[{iface}] Expected bandwidth_limit_mbps=None after clear, "
            f"got {profile.bandwidth_limit_mbps}"
        )
    print(f"✓ get_interface_profiles after clear: all zero for {list(profiles.keys())}")


# ---------------------------------------------------------------------------
# Tests: get_interface_profile (read-only, single interface)
# ---------------------------------------------------------------------------


def test_get_interface_profile_returns_profile(tc: TrafficController) -> None:
    """get_interface_profile(iface) returns an ImpairmentProfile for a specific interface."""
    profile = tc.get_interface_profile(_IFACE_NORTH)

    assert isinstance(profile, ImpairmentProfile), (
        f"Expected ImpairmentProfile, got {type(profile)}"
    )
    print(
        f"✓ get_interface_profile({_IFACE_NORTH!r}): "
        f"latency={profile.latency_ms}ms, loss={profile.loss_percent}%"
    )


def test_get_interface_profile_unknown_interface_raises(tc: TrafficController) -> None:
    """get_interface_profile() raises ValueError for an unknown interface."""
    with pytest.raises(ValueError, match="eth-nonexistent"):
        tc.get_interface_profile("eth-nonexistent")
    print("✓ get_interface_profile('eth-nonexistent') raises ValueError as expected")


# ---------------------------------------------------------------------------
# Tests: set_impairment_profile (symmetric — all interfaces)
# ---------------------------------------------------------------------------


def test_set_impairment_profile_latency_only(tc: TrafficController) -> None:
    """set_impairment_profile applies latency to all interfaces; verified via get_interface_profiles."""
    wanted = ImpairmentProfile(latency_ms=50, jitter_ms=0, loss_percent=0.0, bandwidth_limit_mbps=None)
    tc.set_impairment_profile(wanted)

    profiles = tc.get_interface_profiles()
    for iface, actual in profiles.items():
        _assert_profile_approx(actual, wanted, check_bandwidth=False, label=iface)
    print(f"✓ set_impairment_profile latency_only: 50ms on {list(profiles.keys())}")


def test_set_impairment_profile_latency_and_jitter(tc: TrafficController) -> None:
    """set_impairment_profile with latency + jitter; all interfaces updated."""
    wanted = ImpairmentProfile(latency_ms=20, jitter_ms=5, loss_percent=0.0, bandwidth_limit_mbps=None)
    tc.set_impairment_profile(wanted)

    profiles = tc.get_interface_profiles()
    for iface, actual in profiles.items():
        _assert_profile_approx(actual, wanted, check_bandwidth=False, label=iface)
    print(f"✓ set_impairment_profile latency+jitter: {list(profiles.keys())}")


def test_set_impairment_profile_with_loss(tc: TrafficController) -> None:
    """set_impairment_profile with packet loss; all interfaces updated."""
    wanted = ImpairmentProfile(latency_ms=10, jitter_ms=2, loss_percent=1.5, bandwidth_limit_mbps=None)
    tc.set_impairment_profile(wanted)

    profiles = tc.get_interface_profiles()
    for iface, actual in profiles.items():
        _assert_profile_approx(actual, wanted, check_bandwidth=False, label=iface)
    print(f"✓ set_impairment_profile with loss: 1.5% on {list(profiles.keys())}")


def test_set_impairment_profile_with_bandwidth_limit(tc: TrafficController) -> None:
    """set_impairment_profile with bandwidth cap; all interfaces get TBF qdisc."""
    wanted = ImpairmentProfile(latency_ms=15, jitter_ms=5, loss_percent=0.1, bandwidth_limit_mbps=100)
    tc.set_impairment_profile(wanted)

    profiles = tc.get_interface_profiles()
    for iface, actual in profiles.items():
        _assert_profile_approx(actual, wanted, label=iface)
    print(f"✓ set_impairment_profile with bandwidth: 100Mbps on {list(profiles.keys())}")


def test_set_impairment_profile_from_dict(tc: TrafficController) -> None:
    """set_impairment_profile accepts a plain dict (auto-converts to ImpairmentProfile)."""
    data = {"latency_ms": 30, "jitter_ms": 10, "loss_percent": 0.5, "bandwidth_limit_mbps": None}
    tc.set_impairment_profile(data)

    expected = profile_from_dict(data)
    profiles = tc.get_interface_profiles()
    for iface, actual in profiles.items():
        _assert_profile_approx(actual, expected, check_bandwidth=False, label=iface)
    print(f"✓ set_impairment_profile from dict: {list(profiles.keys())}")


def test_set_impairment_profile_idempotent(tc: TrafficController) -> None:
    """Calling set_impairment_profile twice with the same profile is idempotent."""
    wanted = ImpairmentProfile(latency_ms=25, jitter_ms=8, loss_percent=0.2, bandwidth_limit_mbps=None)
    tc.set_impairment_profile(wanted)
    tc.set_impairment_profile(wanted)

    profiles = tc.get_interface_profiles()
    for iface, actual in profiles.items():
        _assert_profile_approx(actual, wanted, check_bandwidth=False, label=iface)
    print("✓ set_impairment_profile idempotent: second call succeeds")


# ---------------------------------------------------------------------------
# Tests: set_interface_profile (per-interface)
# ---------------------------------------------------------------------------


def test_set_interface_profile_single_interface(tc: TrafficController) -> None:
    """set_interface_profile() applies profile to only the specified interface."""
    tc.clear()

    wanted = ImpairmentProfile(latency_ms=40, jitter_ms=10, loss_percent=0.5, bandwidth_limit_mbps=None)
    tc.set_interface_profile(_IFACE_NORTH, wanted)

    # eth-north should match the profile
    north_profile = tc.get_interface_profile(_IFACE_NORTH)
    _assert_profile_approx(north_profile, wanted, check_bandwidth=False, label=_IFACE_NORTH)

    # eth-dut should still be clear (zero impairment)
    dut_profile = tc.get_interface_profile(_IFACE_DUT)
    assert dut_profile.latency_ms == 0, (
        f"[{_IFACE_DUT}] Expected 0ms (unaffected), got {dut_profile.latency_ms}ms"
    )
    print(
        f"✓ set_interface_profile({_IFACE_NORTH!r}): "
        f"latency={north_profile.latency_ms}ms; {_IFACE_DUT!r} unaffected"
    )


def test_set_interface_profile_asymmetric(tc: TrafficController) -> None:
    """Different profiles on eth-north and eth-dut; each reads back independently."""
    north_profile = ImpairmentProfile(latency_ms=20, jitter_ms=5, loss_percent=0.1, bandwidth_limit_mbps=100)
    dut_profile = ImpairmentProfile(latency_ms=60, jitter_ms=15, loss_percent=1.0, bandwidth_limit_mbps=50)

    tc.set_interface_profile(_IFACE_NORTH, north_profile)
    tc.set_interface_profile(_IFACE_DUT, dut_profile)

    actual_north = tc.get_interface_profile(_IFACE_NORTH)
    actual_dut = tc.get_interface_profile(_IFACE_DUT)

    _assert_profile_approx(actual_north, north_profile, label=_IFACE_NORTH)
    _assert_profile_approx(actual_dut, dut_profile, label=_IFACE_DUT)

    print(
        f"✓ asymmetric profiles: "
        f"{_IFACE_NORTH!r}={actual_north.latency_ms}ms/{actual_north.bandwidth_limit_mbps}Mbps, "
        f"{_IFACE_DUT!r}={actual_dut.latency_ms}ms/{actual_dut.bandwidth_limit_mbps}Mbps"
    )


def test_set_interface_profile_unknown_interface_raises(tc: TrafficController) -> None:
    """set_interface_profile() raises ValueError for an unknown interface."""
    profile = ImpairmentProfile(latency_ms=10, jitter_ms=0, loss_percent=0.0, bandwidth_limit_mbps=None)

    with pytest.raises(ValueError, match="eth-nonexistent"):
        tc.set_interface_profile("eth-nonexistent", profile)
    print("✓ set_interface_profile('eth-nonexistent') raises ValueError as expected")


# ---------------------------------------------------------------------------
# Tests: clear()
# ---------------------------------------------------------------------------


def test_clear_removes_impairment(tc: TrafficController) -> None:
    """clear() removes all tc qdiscs from all interfaces; profiles read back as zero."""
    tc.set_impairment_profile(
        ImpairmentProfile(latency_ms=100, jitter_ms=20, loss_percent=5.0, bandwidth_limit_mbps=50)
    )
    tc.clear()

    profiles = tc.get_interface_profiles()
    for iface, actual in profiles.items():
        assert actual.latency_ms == 0, (
            f"[{iface}] Expected 0ms after clear, got {actual.latency_ms}ms"
        )
        assert actual.loss_percent == 0.0, (
            f"[{iface}] Expected 0% loss after clear, got {actual.loss_percent}%"
        )
        assert actual.bandwidth_limit_mbps is None, (
            f"[{iface}] Expected None bandwidth after clear, got {actual.bandwidth_limit_mbps}"
        )
    print(f"✓ clear: all qdiscs removed on {list(profiles.keys())}")


# ---------------------------------------------------------------------------
# Tests: inject_transient (all interfaces)
# ---------------------------------------------------------------------------


def test_inject_blackout_applies_to_all_and_restores(tc: TrafficController) -> None:
    """inject_transient('blackout') applies 100% loss to all interfaces; auto-restores."""
    baseline = ImpairmentProfile(latency_ms=10, jitter_ms=2, loss_percent=0.5, bandwidth_limit_mbps=None)
    tc.set_impairment_profile(baseline)

    blackout_duration_ms = 1500
    tc.inject_transient("blackout", blackout_duration_ms)

    # Immediately after inject_transient returns, blackout should be active on all ifaces
    profiles_during = tc.get_interface_profiles()
    for iface, profile in profiles_during.items():
        assert profile.loss_percent == 100.0, (
            f"[{iface}] Expected 100% loss during blackout, got {profile.loss_percent}%"
        )
    print(f"✓ inject_blackout active on all: {list(profiles_during.keys())}")

    # Wait for auto-restore (add 1s buffer)
    time.sleep((blackout_duration_ms + 1000) / 1000)

    # After restore, all interfaces should match the baseline
    profiles_after = tc.get_interface_profiles()
    for iface, actual in profiles_after.items():
        _assert_profile_approx(actual, baseline, check_bandwidth=False, label=iface)
    print(f"✓ inject_blackout restored on all: {list(profiles_after.keys())}")


def test_inject_transient_cancelled_by_set_profile(tc: TrafficController) -> None:
    """set_impairment_profile cancels a pending inject_transient restore."""
    baseline = ImpairmentProfile(latency_ms=10, jitter_ms=0, loss_percent=0.0, bandwidth_limit_mbps=None)
    tc.set_impairment_profile(baseline)

    # Start a long-duration blackout
    tc.inject_transient("blackout", duration_ms=10_000)

    # Immediately override with an explicit profile — cancels the pending restore
    override = ImpairmentProfile(latency_ms=50, jitter_ms=0, loss_percent=0.0, bandwidth_limit_mbps=None)
    tc.set_impairment_profile(override)

    # Wait longer than what the blackout would have auto-restored to
    time.sleep(2.0)

    # The override should be active on all ifaces (restore was cancelled)
    profiles = tc.get_interface_profiles()
    for iface, actual in profiles.items():
        assert abs(actual.latency_ms - 50) <= _LATENCY_TOL_MS, (
            f"[{iface}] Expected 50ms (override) after cancel, got {actual.latency_ms}ms"
        )
    print(f"✓ inject_transient cancelled by set_profile: 50ms on {list(profiles.keys())}")


def test_inject_transient_cancelled_by_set_interface_profile(tc: TrafficController) -> None:
    """set_interface_profile cancels a pending inject_transient restore."""
    tc.clear()

    # Start a long-duration blackout
    tc.inject_transient("blackout", duration_ms=10_000)

    # Override one interface — cancels the pending restore for ALL interfaces
    override = ImpairmentProfile(latency_ms=30, jitter_ms=0, loss_percent=0.0, bandwidth_limit_mbps=None)
    tc.set_interface_profile(_IFACE_NORTH, override)

    # Wait to ensure no restore fires
    time.sleep(2.0)

    actual_north = tc.get_interface_profile(_IFACE_NORTH)
    assert abs(actual_north.latency_ms - 30) <= _LATENCY_TOL_MS, (
        f"Expected 30ms (override) on {_IFACE_NORTH!r}, got {actual_north.latency_ms}ms"
    )
    print(
        f"✓ inject_transient cancelled by set_interface_profile: "
        f"{_IFACE_NORTH!r}={actual_north.latency_ms}ms"
    )


def test_inject_brownout(tc: TrafficController) -> None:
    """inject_transient('brownout') applies degraded conditions to all interfaces."""
    tc.clear()
    tc.inject_transient("brownout", duration_ms=5000, latency_ms=200, loss_percent=5.0)

    profiles = tc.get_interface_profiles()
    for iface, profile in profiles.items():
        assert abs(profile.latency_ms - 200) <= _LATENCY_TOL_MS, (
            f"[{iface}] Expected ~200ms during brownout, got {profile.latency_ms}ms"
        )
        assert abs(profile.loss_percent - 5.0) <= _LOSS_TOL_PCT, (
            f"[{iface}] Expected ~5% loss during brownout, got {profile.loss_percent}%"
        )
    print(f"✓ inject_brownout: 200ms/5% on {list(profiles.keys())}")


def test_inject_latency_spike(tc: TrafficController) -> None:
    """inject_transient('latency_spike') applies a high-latency spike to all interfaces."""
    tc.clear()
    tc.inject_transient("latency_spike", duration_ms=5000, spike_latency_ms=500)

    profiles = tc.get_interface_profiles()
    for iface, profile in profiles.items():
        assert abs(profile.latency_ms - 500) <= _LATENCY_TOL_MS * 5, (
            f"[{iface}] Expected ~500ms during latency_spike, got {profile.latency_ms}ms"
        )
    print(f"✓ inject_latency_spike: 500ms on {list(profiles.keys())}")


def test_inject_packet_storm(tc: TrafficController) -> None:
    """inject_transient('packet_storm') applies elevated packet loss to all interfaces."""
    tc.clear()
    tc.inject_transient("packet_storm", duration_ms=5000, loss_percent=10.0)

    profiles = tc.get_interface_profiles()
    for iface, profile in profiles.items():
        assert abs(profile.loss_percent - 10.0) <= _LOSS_TOL_PCT, (
            f"[{iface}] Expected ~10% loss during packet_storm, got {profile.loss_percent}%"
        )
    print(f"✓ inject_packet_storm: 10% loss on {list(profiles.keys())}")
