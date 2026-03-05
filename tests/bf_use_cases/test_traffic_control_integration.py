"""Integration tests for boardfarm3.use_cases.traffic_control.

Exercises all use-case functions end-to-end through the boardfarm device manager
against real ``LinuxTrafficController`` containers.  Requires:

- SD-WAN testbed containers running (``wan1-tc``, ``wan2-tc``)
- Raikou has injected ``eth-north`` and ``eth-dut`` into the TC containers

Run from boardfarm-bdd/ with the venv activated:

    pytest tests/bf_use_cases/test_traffic_control_integration.py -v \\
        --board-name sdwan \\
        --env-config bf_config/bf_env_sdwan.json \\
        --inventory-config bf_config/bf_config_sdwan.json \\
        --legacy --skip-boot

All tests in this module use ``wan1_tc`` via the ``tc`` fixture (defined in
``conftest.py``), which auto-clears impairment after each test.

Named-preset tests use ``boardfarm_config`` (a session-scoped boardfarm fixture)
to resolve preset names from ``environment_def.impairment_presets``.

Preset definitions (from ``bf_env_sdwan.json``)::

    pristine      → latency 5ms / jitter 1ms / loss 0%   / bw 1000 Mbps
    cable_typical → latency 15ms / jitter 5ms / loss 0.1% / bw 100 Mbps
    4g_mobile     → latency 80ms / jitter 30ms / loss 1%  / bw 20 Mbps
    satellite     → latency 600ms / jitter 50ms / loss 2%  / bw 10 Mbps
    congested     → latency 25ms / jitter 40ms / loss 3%  / no bw cap
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

import pytest

import boardfarm3.use_cases.traffic_control as uc
from boardfarm3.exceptions import DeviceNotFound
from boardfarm3.lib.traffic_control import ImpairmentProfile
from boardfarm3.templates.traffic_controller import TrafficController

if TYPE_CHECKING:
    from boardfarm3.lib.boardfarm_config import BoardfarmConfig

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_IFACE_NORTH = "eth-north"
_IFACE_DUT = "eth-dut"

# ---------------------------------------------------------------------------
# Tolerances for round-trip assertion (tc netem rounds internally)
# ---------------------------------------------------------------------------

_LAT_TOL = 1       # ±1 ms for latency / jitter
_LOSS_TOL = 0.01   # ±0.01 % for packet loss
_BW_TOL = 5        # ±5 Mbps for bandwidth (TBF rate rounding)


def _assert_profile(
    actual: ImpairmentProfile,
    *,
    latency_ms: int,
    jitter_ms: int,
    loss_percent: float,
    bandwidth_limit_mbps: int | None = None,
    check_bw: bool = True,
    label: str = "",
) -> None:
    """Assert ImpairmentProfile fields within acceptable tolerances."""
    prefix = f"[{label}] " if label else ""
    assert abs(actual.latency_ms - latency_ms) <= _LAT_TOL, (
        f"{prefix}latency_ms: expected {latency_ms}, got {actual.latency_ms}"
    )
    assert abs(actual.jitter_ms - jitter_ms) <= _LAT_TOL, (
        f"{prefix}jitter_ms: expected {jitter_ms}, got {actual.jitter_ms}"
    )
    assert abs(actual.loss_percent - loss_percent) <= _LOSS_TOL, (
        f"{prefix}loss_percent: expected {loss_percent}, got {actual.loss_percent}"
    )
    if check_bw:
        if bandwidth_limit_mbps is None:
            assert actual.bandwidth_limit_mbps is None, (
                f"{prefix}bandwidth_limit_mbps: expected None, got {actual.bandwidth_limit_mbps}"
            )
        else:
            assert actual.bandwidth_limit_mbps is not None, (
                f"{prefix}bandwidth_limit_mbps: expected non-None, got None"
            )
            assert abs(actual.bandwidth_limit_mbps - bandwidth_limit_mbps) <= _BW_TOL, (
                f"{prefix}bandwidth_limit_mbps: expected {bandwidth_limit_mbps}, "
                f"got {actual.bandwidth_limit_mbps}"
            )


# ---------------------------------------------------------------------------
# get_traffic_controller()
# ---------------------------------------------------------------------------


class TestGetTrafficControllerIntegration:
    """Integration tests for the get_traffic_controller() device getter."""

    def test_get_by_name_wan1_tc(self, devices: object) -> None:
        """get_traffic_controller('wan1_tc') returns a TrafficController."""
        if not getattr(devices, "wan1_tc", None):
            pytest.skip("wan1_tc not in testbed")

        tc = uc.get_traffic_controller("wan1_tc")

        assert isinstance(tc, TrafficController)
        print("✓ get_traffic_controller('wan1_tc') returned a TrafficController")

    def test_get_by_name_wan2_tc(self, devices: object) -> None:
        """get_traffic_controller('wan2_tc') returns a TrafficController."""
        if not getattr(devices, "wan2_tc", None):
            pytest.skip("wan2_tc not in testbed")

        tc = uc.get_traffic_controller("wan2_tc")

        assert isinstance(tc, TrafficController)
        print("✓ get_traffic_controller('wan2_tc') returned a TrafficController")

    def test_no_name_multiple_devices_raises(self, devices: object) -> None:
        """get_traffic_controller() without name raises ValueError when multiple TCs exist."""
        if not (getattr(devices, "wan1_tc", None) and getattr(devices, "wan2_tc", None)):
            pytest.skip("Need both wan1_tc and wan2_tc in testbed")

        with pytest.raises(ValueError, match="Multiple TrafficController"):
            uc.get_traffic_controller()
        print("✓ get_traffic_controller() (no name, multiple TCs) raises ValueError")

    def test_unknown_name_raises_device_not_found(self, devices: object) -> None:
        """get_traffic_controller() with unknown name raises DeviceNotFound."""
        with pytest.raises(DeviceNotFound, match="nonexistent_tc"):
            uc.get_traffic_controller("nonexistent_tc")
        print("✓ get_traffic_controller('nonexistent_tc') raises DeviceNotFound")

    def test_both_wan_tcs_are_independent_instances(self, devices: object) -> None:
        """wan1_tc and wan2_tc are different device instances."""
        if not (getattr(devices, "wan1_tc", None) and getattr(devices, "wan2_tc", None)):
            pytest.skip("Need both wan1_tc and wan2_tc in testbed")

        tc1 = uc.get_traffic_controller("wan1_tc")
        tc2 = uc.get_traffic_controller("wan2_tc")

        assert tc1 is not tc2
        print("✓ wan1_tc and wan2_tc are distinct device instances")


# ---------------------------------------------------------------------------
# get_all_impairment_profiles() / get_impairment_profile()
# ---------------------------------------------------------------------------


class TestGetImpairmentProfileUseCases:
    """Integration tests for profile read use cases."""

    def test_get_all_impairment_profiles_returns_dict(self, tc: TrafficController) -> None:
        """get_all_impairment_profiles() returns a dict with interface names as keys."""
        profiles = uc.get_all_impairment_profiles(tc)

        assert isinstance(profiles, dict)
        assert len(profiles) > 0
        for iface, profile in profiles.items():
            assert isinstance(iface, str)
            assert isinstance(profile, ImpairmentProfile)
        print(f"✓ get_all_impairment_profiles: {list(profiles.keys())}")

    def test_get_impairment_profile_returns_single_interface(self, tc: TrafficController) -> None:
        """get_impairment_profile(tc, iface) returns an ImpairmentProfile for that interface."""
        profile = uc.get_impairment_profile(tc, _IFACE_NORTH)

        assert isinstance(profile, ImpairmentProfile)
        print(
            f"✓ get_impairment_profile({_IFACE_NORTH!r}): "
            f"latency={profile.latency_ms}ms, loss={profile.loss_percent}%"
        )

    def test_get_impairment_profile_both_interfaces_independently(self, tc: TrafficController) -> None:
        """get_impairment_profile can read eth-north and eth-dut independently."""
        north = uc.get_impairment_profile(tc, _IFACE_NORTH)
        dut = uc.get_impairment_profile(tc, _IFACE_DUT)

        assert isinstance(north, ImpairmentProfile)
        assert isinstance(dut, ImpairmentProfile)
        print(
            f"✓ get_impairment_profile independently: "
            f"{_IFACE_NORTH!r}={north.latency_ms}ms, {_IFACE_DUT!r}={dut.latency_ms}ms"
        )


# ---------------------------------------------------------------------------
# set_impairment_profile() / set_interface_profile() / clear_impairment()
# ---------------------------------------------------------------------------


class TestSetImpairmentProfileUseCases:
    """Integration tests for profile set/clear use cases."""

    def test_set_and_get_profile_object_round_trip(self, tc: TrafficController) -> None:
        """set_impairment_profile() with ImpairmentProfile applies to all interfaces."""
        wanted = ImpairmentProfile(latency_ms=25, jitter_ms=8, loss_percent=0.5, bandwidth_limit_mbps=None)

        uc.set_impairment_profile(tc, wanted)

        for iface in [_IFACE_NORTH, _IFACE_DUT]:
            actual = uc.get_impairment_profile(tc, iface)
            _assert_profile(actual, latency_ms=25, jitter_ms=8, loss_percent=0.5, check_bw=False, label=iface)
        print(f"✓ set/get profile round-trip (object): 25ms on both interfaces")

    def test_set_and_get_profile_dict_round_trip(self, tc: TrafficController) -> None:
        """set_impairment_profile() with plain dict applies to all interfaces."""
        data = {"latency_ms": 40, "jitter_ms": 12, "loss_percent": 1.0, "bandwidth_limit_mbps": None}

        uc.set_impairment_profile(tc, data)

        for iface in [_IFACE_NORTH, _IFACE_DUT]:
            actual = uc.get_impairment_profile(tc, iface)
            _assert_profile(actual, latency_ms=40, jitter_ms=12, loss_percent=1.0, check_bw=False, label=iface)
        print(f"✓ set/get profile round-trip (dict): 40ms on both interfaces")

    def test_set_profile_with_bandwidth_limit(self, tc: TrafficController) -> None:
        """set_impairment_profile() with bandwidth cap; TBF qdisc on all interfaces."""
        wanted = ImpairmentProfile(latency_ms=15, jitter_ms=5, loss_percent=0.1, bandwidth_limit_mbps=100)

        uc.set_impairment_profile(tc, wanted)

        for iface in [_IFACE_NORTH, _IFACE_DUT]:
            actual = uc.get_impairment_profile(tc, iface)
            _assert_profile(
                actual, latency_ms=15, jitter_ms=5, loss_percent=0.1,
                bandwidth_limit_mbps=100, label=iface
            )
        print(f"✓ set profile with bandwidth: 100Mbps on both interfaces")

    def test_clear_impairment_zeroes_all_profiles(self, tc: TrafficController) -> None:
        """clear_impairment() removes all qdiscs; all interfaces read back as zero."""
        uc.set_impairment_profile(
            tc,
            ImpairmentProfile(latency_ms=50, jitter_ms=10, loss_percent=2.0, bandwidth_limit_mbps=100),
        )

        uc.clear_impairment(tc)

        for iface in [_IFACE_NORTH, _IFACE_DUT]:
            actual = uc.get_impairment_profile(tc, iface)
            assert actual.latency_ms == 0, f"[{iface}] Expected 0ms after clear"
            assert actual.loss_percent == 0.0, f"[{iface}] Expected 0% after clear"
            assert actual.bandwidth_limit_mbps is None, f"[{iface}] Expected None bw after clear"
        print("✓ clear_impairment: all qdiscs removed on both interfaces")

    def test_set_profile_idempotent(self, tc: TrafficController) -> None:
        """Calling set_impairment_profile twice with same args is idempotent."""
        wanted = ImpairmentProfile(latency_ms=30, jitter_ms=10, loss_percent=0.3, bandwidth_limit_mbps=None)

        uc.set_impairment_profile(tc, wanted)
        uc.set_impairment_profile(tc, wanted)

        for iface in [_IFACE_NORTH, _IFACE_DUT]:
            actual = uc.get_impairment_profile(tc, iface)
            _assert_profile(actual, latency_ms=30, jitter_ms=10, loss_percent=0.3, check_bw=False, label=iface)
        print("✓ set_impairment_profile is idempotent")


class TestSetInterfaceProfileUseCases:
    """Integration tests for per-interface set_interface_profile() use case."""

    def test_set_interface_profile_single_interface_only(self, tc: TrafficController) -> None:
        """set_interface_profile() applies only to the specified interface."""
        uc.clear_impairment(tc)

        wanted = ImpairmentProfile(latency_ms=40, jitter_ms=10, loss_percent=0.5, bandwidth_limit_mbps=None)
        uc.set_interface_profile(tc, _IFACE_NORTH, wanted)

        north = uc.get_impairment_profile(tc, _IFACE_NORTH)
        _assert_profile(north, latency_ms=40, jitter_ms=10, loss_percent=0.5, check_bw=False, label=_IFACE_NORTH)

        dut = uc.get_impairment_profile(tc, _IFACE_DUT)
        assert dut.latency_ms == 0, (
            f"[{_IFACE_DUT}] Expected 0ms (unaffected), got {dut.latency_ms}ms"
        )
        print(
            f"✓ set_interface_profile({_IFACE_NORTH!r}): "
            f"40ms applied; {_IFACE_DUT!r} unaffected"
        )

    def test_set_interface_profile_asymmetric_bw(self, tc: TrafficController) -> None:
        """Different bandwidth caps on eth-north and eth-dut (asymmetric link simulation)."""
        north_profile = ImpairmentProfile(latency_ms=20, jitter_ms=5, loss_percent=0.1, bandwidth_limit_mbps=100)
        dut_profile = ImpairmentProfile(latency_ms=20, jitter_ms=5, loss_percent=0.1, bandwidth_limit_mbps=50)

        uc.set_interface_profile(tc, _IFACE_NORTH, north_profile)
        uc.set_interface_profile(tc, _IFACE_DUT, dut_profile)

        actual_north = uc.get_impairment_profile(tc, _IFACE_NORTH)
        actual_dut = uc.get_impairment_profile(tc, _IFACE_DUT)

        _assert_profile(actual_north, latency_ms=20, jitter_ms=5, loss_percent=0.1,
                        bandwidth_limit_mbps=100, label=_IFACE_NORTH)
        _assert_profile(actual_dut, latency_ms=20, jitter_ms=5, loss_percent=0.1,
                        bandwidth_limit_mbps=50, label=_IFACE_DUT)

        print(
            f"✓ asymmetric bw: {_IFACE_NORTH!r}={actual_north.bandwidth_limit_mbps}Mbps, "
            f"{_IFACE_DUT!r}={actual_dut.bandwidth_limit_mbps}Mbps"
        )

    def test_set_interface_profile_all_interfaces_dict(self, tc: TrafficController) -> None:
        """get_all_impairment_profiles() reflects per-interface profiles set individually."""
        north_profile = ImpairmentProfile(latency_ms=30, jitter_ms=5, loss_percent=0.0, bandwidth_limit_mbps=None)
        dut_profile = ImpairmentProfile(latency_ms=80, jitter_ms=20, loss_percent=0.5, bandwidth_limit_mbps=None)

        uc.set_interface_profile(tc, _IFACE_NORTH, north_profile)
        uc.set_interface_profile(tc, _IFACE_DUT, dut_profile)

        profiles = uc.get_all_impairment_profiles(tc)

        assert _IFACE_NORTH in profiles
        assert _IFACE_DUT in profiles
        _assert_profile(profiles[_IFACE_NORTH], latency_ms=30, jitter_ms=5, loss_percent=0.0,
                        check_bw=False, label=_IFACE_NORTH)
        _assert_profile(profiles[_IFACE_DUT], latency_ms=80, jitter_ms=20, loss_percent=0.5,
                        check_bw=False, label=_IFACE_DUT)
        print("✓ get_all_impairment_profiles reflects per-interface profiles")


# ---------------------------------------------------------------------------
# apply_preset()
# ---------------------------------------------------------------------------


class TestApplyPresetIntegration:
    """Integration tests for apply_preset() use case."""

    def test_apply_cable_typical_preset(self, tc: TrafficController, boardfarm_config: BoardfarmConfig) -> None:
        """apply_preset('cable_typical') applies 15ms / 5ms / 0.1% / 100Mbps to all interfaces."""
        uc.apply_preset(tc, "cable_typical", boardfarm_config)

        for iface in [_IFACE_NORTH, _IFACE_DUT]:
            actual = uc.get_impairment_profile(tc, iface)
            _assert_profile(actual, latency_ms=15, jitter_ms=5, loss_percent=0.1,
                            bandwidth_limit_mbps=100, label=iface)
        print(f"✓ apply_preset(cable_typical): 15ms/0.1%/100Mbps on both interfaces")

    def test_apply_satellite_preset(self, tc: TrafficController, boardfarm_config: BoardfarmConfig) -> None:
        """apply_preset('satellite') applies high latency and loss."""
        uc.apply_preset(tc, "satellite", boardfarm_config)

        for iface in [_IFACE_NORTH, _IFACE_DUT]:
            actual = uc.get_impairment_profile(tc, iface)
            _assert_profile(actual, latency_ms=600, jitter_ms=50, loss_percent=2.0,
                            bandwidth_limit_mbps=10, label=iface)
        print(f"✓ apply_preset(satellite): 600ms/2%/10Mbps on both interfaces")

    def test_apply_4g_mobile_preset(self, tc: TrafficController, boardfarm_config: BoardfarmConfig) -> None:
        """apply_preset('4g_mobile') applies 80ms / 30ms jitter / 1% loss."""
        uc.apply_preset(tc, "4g_mobile", boardfarm_config)

        for iface in [_IFACE_NORTH, _IFACE_DUT]:
            actual = uc.get_impairment_profile(tc, iface)
            _assert_profile(actual, latency_ms=80, jitter_ms=30, loss_percent=1.0,
                            bandwidth_limit_mbps=20, label=iface)
        print(f"✓ apply_preset(4g_mobile): 80ms/1%/20Mbps on both interfaces")

    def test_apply_congested_preset_no_bandwidth_cap(self, tc: TrafficController, boardfarm_config: BoardfarmConfig) -> None:
        """apply_preset('congested') applies no bandwidth cap (null in env config)."""
        uc.apply_preset(tc, "congested", boardfarm_config)

        for iface in [_IFACE_NORTH, _IFACE_DUT]:
            actual = uc.get_impairment_profile(tc, iface)
            _assert_profile(actual, latency_ms=25, jitter_ms=40, loss_percent=3.0,
                            bandwidth_limit_mbps=None, label=iface)
        print(f"✓ apply_preset(congested): 25ms/3%/no bw cap on both interfaces")

    def test_apply_pristine_preset(self, tc: TrafficController, boardfarm_config: BoardfarmConfig) -> None:
        """apply_preset('pristine') applies near-zero impairment baseline."""
        uc.apply_preset(tc, "pristine", boardfarm_config)

        for iface in [_IFACE_NORTH, _IFACE_DUT]:
            actual = uc.get_impairment_profile(tc, iface)
            _assert_profile(actual, latency_ms=5, jitter_ms=1, loss_percent=0.0,
                            bandwidth_limit_mbps=1000, label=iface)
        print(f"✓ apply_preset(pristine): 5ms/0%/1000Mbps on both interfaces")

    def test_apply_unknown_preset_raises(self, tc: TrafficController, boardfarm_config: BoardfarmConfig) -> None:
        """apply_preset() with an unknown preset name raises KeyError."""
        with pytest.raises(KeyError, match="no_such_preset"):
            uc.apply_preset(tc, "no_such_preset", boardfarm_config)
        print("✓ apply_preset('no_such_preset') raises KeyError as expected")

    def test_apply_preset_transient_duration(self, tc: TrafficController, boardfarm_config: BoardfarmConfig) -> None:
        """apply_preset with duration_ms applies as a timed transient; auto-restores."""
        baseline = ImpairmentProfile(latency_ms=5, jitter_ms=1, loss_percent=0.0, bandwidth_limit_mbps=None)
        uc.set_impairment_profile(tc, baseline)

        transient_duration_ms = 1500
        uc.apply_preset(tc, "cable_typical", boardfarm_config, duration_ms=transient_duration_ms)

        # Transient should be active on both interfaces
        for iface in [_IFACE_NORTH, _IFACE_DUT]:
            during = uc.get_impairment_profile(tc, iface)
            assert during.latency_ms > baseline.latency_ms, (
                f"[{iface}] Expected transient latency > baseline ({baseline.latency_ms}ms), "
                f"got {during.latency_ms}ms"
            )
        print(f"✓ apply_preset transient active on both interfaces")

        # After restore, baseline should be restored on both interfaces
        time.sleep((transient_duration_ms + 1000) / 1000)
        for iface in [_IFACE_NORTH, _IFACE_DUT]:
            after = uc.get_impairment_profile(tc, iface)
            assert abs(after.latency_ms - baseline.latency_ms) <= _LAT_TOL, (
                f"[{iface}] Expected baseline restored ({baseline.latency_ms}ms), "
                f"got {after.latency_ms}ms"
            )
        print(f"✓ apply_preset transient restored on both interfaces")


# ---------------------------------------------------------------------------
# inject_blackout() / inject_brownout() / inject_latency_spike() / inject_packet_storm()
# ---------------------------------------------------------------------------


class TestTransientEventUseCases:
    """Integration tests for transient event injection use cases."""

    def test_inject_blackout_active_and_restores(self, tc: TrafficController) -> None:
        """inject_blackout() applies 100% loss to all interfaces; auto-restores after duration."""
        baseline = ImpairmentProfile(latency_ms=10, jitter_ms=2, loss_percent=0.5, bandwidth_limit_mbps=None)
        uc.set_impairment_profile(tc, baseline)

        duration_ms = 1500
        uc.inject_blackout(tc, duration_ms=duration_ms)

        for iface in [_IFACE_NORTH, _IFACE_DUT]:
            during = uc.get_impairment_profile(tc, iface)
            assert during.loss_percent == 100.0, (
                f"[{iface}] Expected 100% loss during blackout, got {during.loss_percent}%"
            )
        print(f"✓ inject_blackout active: 100% loss on both interfaces")

        time.sleep((duration_ms + 1000) / 1000)

        for iface in [_IFACE_NORTH, _IFACE_DUT]:
            after = uc.get_impairment_profile(tc, iface)
            _assert_profile(after, latency_ms=10, jitter_ms=2, loss_percent=0.5, check_bw=False, label=iface)
        print(f"✓ inject_blackout restored on both interfaces")

    def test_inject_brownout_default_params(self, tc: TrafficController) -> None:
        """inject_brownout() with defaults: 200ms latency, 5% loss on all interfaces."""
        uc.clear_impairment(tc)

        uc.inject_brownout(tc, duration_ms=5000)

        for iface in [_IFACE_NORTH, _IFACE_DUT]:
            during = uc.get_impairment_profile(tc, iface)
            assert abs(during.latency_ms - 200) <= _LAT_TOL, (
                f"[{iface}] Expected ~200ms during brownout, got {during.latency_ms}ms"
            )
            assert abs(during.loss_percent - 5.0) <= _LOSS_TOL, (
                f"[{iface}] Expected ~5% loss during brownout, got {during.loss_percent}%"
            )
        print(f"✓ inject_brownout(defaults): 200ms/5% on both interfaces")

    def test_inject_brownout_custom_params(self, tc: TrafficController) -> None:
        """inject_brownout() with custom latency_ms and loss_percent."""
        uc.clear_impairment(tc)

        uc.inject_brownout(tc, duration_ms=5000, latency_ms=100, loss_percent=3.0)

        for iface in [_IFACE_NORTH, _IFACE_DUT]:
            during = uc.get_impairment_profile(tc, iface)
            assert abs(during.latency_ms - 100) <= _LAT_TOL, (
                f"[{iface}] Expected ~100ms, got {during.latency_ms}ms"
            )
            assert abs(during.loss_percent - 3.0) <= _LOSS_TOL, (
                f"[{iface}] Expected ~3% loss, got {during.loss_percent}%"
            )
        print(f"✓ inject_brownout(custom): 100ms/3% on both interfaces")

    def test_inject_latency_spike_default_params(self, tc: TrafficController) -> None:
        """inject_latency_spike() with default spike_latency_ms=500."""
        uc.clear_impairment(tc)

        uc.inject_latency_spike(tc, duration_ms=5000)

        for iface in [_IFACE_NORTH, _IFACE_DUT]:
            during = uc.get_impairment_profile(tc, iface)
            assert abs(during.latency_ms - 500) <= _LAT_TOL * 5, (
                f"[{iface}] Expected ~500ms spike, got {during.latency_ms}ms"
            )
        print(f"✓ inject_latency_spike(default): 500ms on both interfaces")

    def test_inject_latency_spike_custom_params(self, tc: TrafficController) -> None:
        """inject_latency_spike() with custom spike_latency_ms."""
        uc.clear_impairment(tc)

        uc.inject_latency_spike(tc, duration_ms=5000, spike_latency_ms=200)

        for iface in [_IFACE_NORTH, _IFACE_DUT]:
            during = uc.get_impairment_profile(tc, iface)
            assert abs(during.latency_ms - 200) <= _LAT_TOL * 3, (
                f"[{iface}] Expected ~200ms spike, got {during.latency_ms}ms"
            )
        print(f"✓ inject_latency_spike(custom 200ms): 200ms on both interfaces")

    def test_inject_packet_storm_default_params(self, tc: TrafficController) -> None:
        """inject_packet_storm() with default loss_percent=10.0."""
        uc.clear_impairment(tc)

        uc.inject_packet_storm(tc, duration_ms=5000)

        for iface in [_IFACE_NORTH, _IFACE_DUT]:
            during = uc.get_impairment_profile(tc, iface)
            assert abs(during.loss_percent - 10.0) <= _LOSS_TOL, (
                f"[{iface}] Expected ~10% loss during packet storm, got {during.loss_percent}%"
            )
        print(f"✓ inject_packet_storm(default): 10% loss on both interfaces")

    def test_inject_packet_storm_custom_params(self, tc: TrafficController) -> None:
        """inject_packet_storm() with custom loss_percent."""
        uc.clear_impairment(tc)

        uc.inject_packet_storm(tc, duration_ms=5000, loss_percent=20.0)

        for iface in [_IFACE_NORTH, _IFACE_DUT]:
            during = uc.get_impairment_profile(tc, iface)
            assert abs(during.loss_percent - 20.0) <= _LOSS_TOL, (
                f"[{iface}] Expected ~20% loss, got {during.loss_percent}%"
            )
        print(f"✓ inject_packet_storm(custom 20%): 20% loss on both interfaces")

    def test_second_inject_cancels_first_restore(self, tc: TrafficController) -> None:
        """A second use-case call cancels the pending restore from the first."""
        uc.clear_impairment(tc)

        # Start a long blackout
        uc.inject_blackout(tc, duration_ms=10_000)

        # Immediately override with a brownout — this should cancel the blackout restore
        uc.inject_brownout(tc, duration_ms=5000, latency_ms=150, loss_percent=3.0)

        # Wait longer than the original blackout would have restored to
        time.sleep(2.0)

        for iface in [_IFACE_NORTH, _IFACE_DUT]:
            during = uc.get_impairment_profile(tc, iface)
            assert during.loss_percent < 100.0, (
                f"[{iface}] Blackout restore was not cancelled; still 100% loss after 2s"
            )
            assert abs(during.latency_ms - 150) <= _LAT_TOL * 3, (
                f"[{iface}] Expected brownout latency ~150ms, got {during.latency_ms}ms"
            )
        print(f"✓ second inject cancels first restore: brownout active on both interfaces")
