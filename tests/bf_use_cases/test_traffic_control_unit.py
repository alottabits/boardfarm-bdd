"""Unit tests for boardfarm3.use_cases.traffic_control.

Tests the use-case layer in complete isolation using ``unittest.mock``.
No boardfarm infrastructure, no running containers, and no network access
are required.  Every dependency on the device manager, devices, and
boardfarm config is replaced by ``MagicMock`` / ``patch``.

Run without any boardfarm flags:

    pytest tests/bf_use_cases/test_traffic_control_unit.py -v

Coverage:
- ``get_traffic_controller()``          — device selection, error paths
- ``_get_preset_from_config()``         — preset resolution and error path
- ``apply_preset()``                    — sustained and transient variants
- ``set_impairment_profile()``          — symmetric thin wrapper
- ``set_interface_profile()``           — per-interface thin wrapper
- ``get_impairment_profile()``          — per-interface thin wrapper
- ``get_all_impairment_profiles()``     — all-interfaces thin wrapper
- ``clear_impairment()``                — thin wrapper delegation
- ``inject_blackout()``                 — correct event + duration passed
- ``inject_brownout()``                 — defaults and custom kwargs
- ``inject_latency_spike()``            — defaults and custom kwargs
- ``inject_packet_storm()``             — defaults and custom kwargs
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from boardfarm3.exceptions import DeviceNotFound
from boardfarm3.lib.traffic_control import ImpairmentProfile
from boardfarm3.templates.traffic_controller import TrafficController
from boardfarm3.use_cases import traffic_control as uc
from boardfarm3.use_cases.traffic_control import _get_preset_from_config

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_PRESETS = {
    "cable_typical": {"latency_ms": 15, "jitter_ms": 5, "loss_percent": 0.1, "bandwidth_limit_mbps": 100},
    "satellite":     {"latency_ms": 600, "jitter_ms": 50, "loss_percent": 2, "bandwidth_limit_mbps": 10},
    "event_preset":  {"event": "latency_spike", "latency_ms": 300, "jitter_ms": 10, "loss_percent": 0, "bandwidth_limit_mbps": None},
}

_IFACE_NORTH = "eth-north"
_IFACE_DUT = "eth-dut"


def _make_mock_tc() -> MagicMock:
    """Return a MagicMock with the TrafficController spec."""
    return MagicMock(spec=TrafficController)


def _make_mock_config(presets: dict | None = None) -> MagicMock:
    """Return a mock BoardfarmConfig with the given preset dict.

    Pass an explicit dict (including ``{}``) to override _PRESETS.
    Omit (or pass ``None``) to use the module-level _PRESETS default.
    ``presets or _PRESETS`` is intentionally avoided: an empty dict is falsy.
    """
    cfg = MagicMock()
    cfg.env_config = {
        "environment_def": {
            "impairment_presets": dict(_PRESETS if presets is None else presets)
        }
    }
    return cfg


def _make_profile(
    latency_ms: int = 10,
    jitter_ms: int = 2,
    loss_percent: float = 0.1,
    bandwidth_limit_mbps: int | None = None,
) -> ImpairmentProfile:
    """Convenience constructor for test profiles."""
    return ImpairmentProfile(
        latency_ms=latency_ms,
        jitter_ms=jitter_ms,
        loss_percent=loss_percent,
        bandwidth_limit_mbps=bandwidth_limit_mbps,
    )


# ---------------------------------------------------------------------------
# get_traffic_controller()
# ---------------------------------------------------------------------------


class TestGetTrafficController:
    """Tests for get_traffic_controller() device selection logic."""

    @patch("boardfarm3.use_cases.traffic_control.get_device_manager")
    def test_single_device_no_name(self, mock_gdm: MagicMock) -> None:
        """Returns the sole TC when exactly one device is registered and name=None."""
        mock_tc = _make_mock_tc()
        mock_gdm.return_value.get_devices_by_type.return_value = {"wan1_tc": mock_tc}

        result = uc.get_traffic_controller()

        assert result is mock_tc

    @patch("boardfarm3.use_cases.traffic_control.get_device_manager")
    def test_named_device_selected(self, mock_gdm: MagicMock) -> None:
        """Returns the named TC when multiple devices are registered."""
        mock_tc1 = _make_mock_tc()
        mock_tc2 = _make_mock_tc()
        mock_gdm.return_value.get_devices_by_type.return_value = {
            "wan1_tc": mock_tc1,
            "wan2_tc": mock_tc2,
        }

        result = uc.get_traffic_controller("wan2_tc")

        assert result is mock_tc2

    @patch("boardfarm3.use_cases.traffic_control.get_device_manager")
    def test_no_devices_raises_device_not_found(self, mock_gdm: MagicMock) -> None:
        """Raises DeviceNotFound when no TrafficController devices are registered."""
        mock_gdm.return_value.get_devices_by_type.return_value = {}

        with pytest.raises(DeviceNotFound, match="No TrafficController"):
            uc.get_traffic_controller()

    @patch("boardfarm3.use_cases.traffic_control.get_device_manager")
    def test_unknown_name_raises_device_not_found(self, mock_gdm: MagicMock) -> None:
        """Raises DeviceNotFound when name= does not match any registered device."""
        mock_gdm.return_value.get_devices_by_type.return_value = {"wan1_tc": _make_mock_tc()}

        with pytest.raises(DeviceNotFound, match="wan99_tc"):
            uc.get_traffic_controller("wan99_tc")

    @patch("boardfarm3.use_cases.traffic_control.get_device_manager")
    def test_multiple_devices_no_name_raises_value_error(self, mock_gdm: MagicMock) -> None:
        """Raises ValueError when multiple TCs exist and name=None."""
        mock_gdm.return_value.get_devices_by_type.return_value = {
            "wan1_tc": _make_mock_tc(),
            "wan2_tc": _make_mock_tc(),
        }

        with pytest.raises(ValueError, match="Multiple TrafficController"):
            uc.get_traffic_controller()

    @patch("boardfarm3.use_cases.traffic_control.get_device_manager")
    def test_error_message_lists_available_devices_for_unknown_name(self, mock_gdm: MagicMock) -> None:
        """DeviceNotFound message lists available device names."""
        mock_gdm.return_value.get_devices_by_type.return_value = {
            "wan1_tc": _make_mock_tc(),
            "wan2_tc": _make_mock_tc(),
        }

        with pytest.raises(DeviceNotFound) as exc_info:
            uc.get_traffic_controller("lte_tc")

        msg = str(exc_info.value)
        assert "lte_tc" in msg
        assert "wan1_tc" in msg or "wan2_tc" in msg


# ---------------------------------------------------------------------------
# _get_preset_from_config()
# ---------------------------------------------------------------------------


class TestGetPresetFromConfig:
    """Tests for _get_preset_from_config() preset resolution."""

    def test_known_preset_returned(self) -> None:
        """Returns the preset dict for a known preset name."""
        cfg = _make_mock_config()

        result = _get_preset_from_config(cfg, "cable_typical")

        assert result["latency_ms"] == 15
        assert result["jitter_ms"] == 5
        assert result["loss_percent"] == 0.1
        assert result["bandwidth_limit_mbps"] == 100

    def test_unknown_preset_raises_key_error(self) -> None:
        """Raises KeyError for an unknown preset name."""
        cfg = _make_mock_config()

        with pytest.raises(KeyError, match="no_such_preset"):
            _get_preset_from_config(cfg, "no_such_preset")

    def test_error_message_lists_available_presets(self) -> None:
        """KeyError message lists available preset names."""
        cfg = _make_mock_config(
            {"only_preset": {"latency_ms": 10, "jitter_ms": 0, "loss_percent": 0, "bandwidth_limit_mbps": None}}
        )

        with pytest.raises(KeyError) as exc_info:
            _get_preset_from_config(cfg, "missing")

        assert "only_preset" in str(exc_info.value)

    def test_empty_presets_raises_key_error(self) -> None:
        """Raises KeyError when no presets are defined."""
        cfg = _make_mock_config({})

        with pytest.raises(KeyError):
            _get_preset_from_config(cfg, "cable_typical")


# ---------------------------------------------------------------------------
# apply_preset()
# ---------------------------------------------------------------------------


class TestApplyPreset:
    """Tests for apply_preset() preset application."""

    def test_sustained_calls_set_impairment_profile(self) -> None:
        """Without duration_ms, calls controller.set_impairment_profile with parsed preset."""
        mock_tc = _make_mock_tc()
        cfg = _make_mock_config()

        uc.apply_preset(mock_tc, "cable_typical", cfg)

        mock_tc.set_impairment_profile.assert_called_once()
        profile_arg = mock_tc.set_impairment_profile.call_args[0][0]
        assert isinstance(profile_arg, ImpairmentProfile)
        assert profile_arg.latency_ms == 15
        assert profile_arg.jitter_ms == 5
        assert profile_arg.loss_percent == 0.1
        assert profile_arg.bandwidth_limit_mbps == 100

    def test_sustained_does_not_call_inject_transient(self) -> None:
        """Without duration_ms, inject_transient is NOT called."""
        mock_tc = _make_mock_tc()
        uc.apply_preset(mock_tc, "satellite", _make_mock_config())

        mock_tc.inject_transient.assert_not_called()

    def test_transient_calls_inject_transient_with_duration(self) -> None:
        """With duration_ms, calls controller.inject_transient with the duration."""
        mock_tc = _make_mock_tc()
        cfg = _make_mock_config()

        uc.apply_preset(mock_tc, "cable_typical", cfg, duration_ms=3000)

        mock_tc.inject_transient.assert_called_once()
        _, duration_arg = mock_tc.inject_transient.call_args[0]
        assert duration_arg == 3000

    def test_transient_uses_default_brownout_event(self) -> None:
        """Transient preset without 'event' key defaults to 'brownout' event."""
        mock_tc = _make_mock_tc()
        cfg = _make_mock_config()

        uc.apply_preset(mock_tc, "cable_typical", cfg, duration_ms=2000)

        event_arg = mock_tc.inject_transient.call_args[0][0]
        assert event_arg == "brownout"

    def test_transient_uses_event_key_from_preset(self) -> None:
        """Transient preset with 'event' key uses that event type."""
        mock_tc = _make_mock_tc()
        cfg = _make_mock_config()

        uc.apply_preset(mock_tc, "event_preset", cfg, duration_ms=1500)

        event_arg = mock_tc.inject_transient.call_args[0][0]
        assert event_arg == "latency_spike"

    def test_transient_passes_preset_fields_as_kwargs(self) -> None:
        """Remaining preset fields are passed as kwargs to inject_transient."""
        mock_tc = _make_mock_tc()
        cfg = _make_mock_config()

        uc.apply_preset(mock_tc, "cable_typical", cfg, duration_ms=1000)

        kwargs = mock_tc.inject_transient.call_args[1]
        assert kwargs["latency_ms"] == 15
        assert kwargs["jitter_ms"] == 5
        assert kwargs["loss_percent"] == 0.1

    def test_transient_does_not_call_set_impairment_profile(self) -> None:
        """With duration_ms, set_impairment_profile is NOT called."""
        mock_tc = _make_mock_tc()
        uc.apply_preset(mock_tc, "cable_typical", _make_mock_config(), duration_ms=1000)

        mock_tc.set_impairment_profile.assert_not_called()


# ---------------------------------------------------------------------------
# Symmetric wrappers: set_impairment_profile() / clear_impairment()
# ---------------------------------------------------------------------------


class TestSymmetricWrappers:
    """Tests for symmetric thin wrapper use-case functions."""

    def test_set_impairment_profile_delegates_profile_object(self) -> None:
        """set_impairment_profile() calls controller.set_impairment_profile(profile)."""
        mock_tc = _make_mock_tc()
        profile = _make_profile(latency_ms=20, jitter_ms=5, loss_percent=0.1)

        uc.set_impairment_profile(mock_tc, profile)

        mock_tc.set_impairment_profile.assert_called_once_with(profile)

    def test_set_impairment_profile_delegates_dict(self) -> None:
        """set_impairment_profile() passes a dict through unchanged."""
        mock_tc = _make_mock_tc()
        data = {"latency_ms": 10, "jitter_ms": 2, "loss_percent": 0.5, "bandwidth_limit_mbps": None}

        uc.set_impairment_profile(mock_tc, data)

        mock_tc.set_impairment_profile.assert_called_once_with(data)

    def test_clear_impairment_delegates(self) -> None:
        """clear_impairment() calls controller.clear()."""
        mock_tc = _make_mock_tc()

        uc.clear_impairment(mock_tc)

        mock_tc.clear.assert_called_once_with()


# ---------------------------------------------------------------------------
# Per-interface wrappers: set_interface_profile() / get_impairment_profile() /
#                         get_all_impairment_profiles()
# ---------------------------------------------------------------------------


class TestPerInterfaceWrappers:
    """Tests for per-interface thin wrapper use-case functions."""

    def test_set_interface_profile_delegates(self) -> None:
        """set_interface_profile() calls controller.set_interface_profile(interface, profile)."""
        mock_tc = _make_mock_tc()
        profile = _make_profile(latency_ms=30)

        uc.set_interface_profile(mock_tc, _IFACE_NORTH, profile)

        mock_tc.set_interface_profile.assert_called_once_with(_IFACE_NORTH, profile)

    def test_set_interface_profile_delegates_dict(self) -> None:
        """set_interface_profile() passes a dict through unchanged."""
        mock_tc = _make_mock_tc()
        data = {"latency_ms": 50, "jitter_ms": 10, "loss_percent": 0.2, "bandwidth_limit_mbps": 100}

        uc.set_interface_profile(mock_tc, _IFACE_DUT, data)

        mock_tc.set_interface_profile.assert_called_once_with(_IFACE_DUT, data)

    def test_get_impairment_profile_delegates_and_returns(self) -> None:
        """get_impairment_profile() calls controller.get_interface_profile(interface) and returns."""
        mock_tc = _make_mock_tc()
        expected = _make_profile(latency_ms=30, jitter_ms=8, loss_percent=0.2)
        mock_tc.get_interface_profile.return_value = expected

        result = uc.get_impairment_profile(mock_tc, _IFACE_NORTH)

        assert result is expected
        mock_tc.get_interface_profile.assert_called_once_with(_IFACE_NORTH)

    def test_get_impairment_profile_passes_correct_interface(self) -> None:
        """get_impairment_profile() passes the correct interface name to the device."""
        mock_tc = _make_mock_tc()
        mock_tc.get_interface_profile.return_value = _make_profile()

        uc.get_impairment_profile(mock_tc, _IFACE_DUT)

        mock_tc.get_interface_profile.assert_called_once_with(_IFACE_DUT)

    def test_get_all_impairment_profiles_delegates_and_returns(self) -> None:
        """get_all_impairment_profiles() calls controller.get_interface_profiles() and returns."""
        mock_tc = _make_mock_tc()
        expected = {
            _IFACE_NORTH: _make_profile(latency_ms=10),
            _IFACE_DUT: _make_profile(latency_ms=20),
        }
        mock_tc.get_interface_profiles.return_value = expected

        result = uc.get_all_impairment_profiles(mock_tc)

        assert result is expected
        mock_tc.get_interface_profiles.assert_called_once_with()


# ---------------------------------------------------------------------------
# inject_blackout()
# ---------------------------------------------------------------------------


class TestInjectBlackout:
    """Tests for inject_blackout()."""

    def test_calls_inject_transient_blackout(self) -> None:
        """Calls controller.inject_transient('blackout', duration_ms)."""
        mock_tc = _make_mock_tc()

        uc.inject_blackout(mock_tc, duration_ms=2000)

        mock_tc.inject_transient.assert_called_once_with("blackout", 2000)

    def test_no_extra_kwargs_passed(self) -> None:
        """inject_blackout passes no extra kwargs to inject_transient."""
        mock_tc = _make_mock_tc()

        uc.inject_blackout(mock_tc, duration_ms=500)

        _, kwargs = mock_tc.inject_transient.call_args
        assert kwargs == {}

    @pytest.mark.parametrize("duration_ms", [100, 1000, 5000, 30_000])
    def test_duration_passed_correctly(self, duration_ms: int) -> None:
        """Correct duration_ms is passed to inject_transient."""
        mock_tc = _make_mock_tc()

        uc.inject_blackout(mock_tc, duration_ms=duration_ms)

        assert mock_tc.inject_transient.call_args[0] == ("blackout", duration_ms)


# ---------------------------------------------------------------------------
# inject_brownout()
# ---------------------------------------------------------------------------


class TestInjectBrownout:
    """Tests for inject_brownout()."""

    def test_default_latency_and_loss(self) -> None:
        """Default args: latency_ms=200, loss_percent=5.0."""
        mock_tc = _make_mock_tc()

        uc.inject_brownout(mock_tc, duration_ms=3000)

        mock_tc.inject_transient.assert_called_once_with(
            "brownout", 3000, latency_ms=200, loss_percent=5.0
        )

    def test_custom_latency_and_loss(self) -> None:
        """Custom args override the defaults."""
        mock_tc = _make_mock_tc()

        uc.inject_brownout(mock_tc, duration_ms=1000, latency_ms=150, loss_percent=8.0)

        mock_tc.inject_transient.assert_called_once_with(
            "brownout", 1000, latency_ms=150, loss_percent=8.0
        )

    def test_event_type_is_brownout(self) -> None:
        """Event type passed to inject_transient is 'brownout'."""
        mock_tc = _make_mock_tc()

        uc.inject_brownout(mock_tc, duration_ms=500)

        assert mock_tc.inject_transient.call_args[0][0] == "brownout"


# ---------------------------------------------------------------------------
# inject_latency_spike()
# ---------------------------------------------------------------------------


class TestInjectLatencySpike:
    """Tests for inject_latency_spike()."""

    def test_default_spike_latency(self) -> None:
        """Default spike_latency_ms=500."""
        mock_tc = _make_mock_tc()

        uc.inject_latency_spike(mock_tc, duration_ms=2000)

        mock_tc.inject_transient.assert_called_once_with(
            "latency_spike", 2000, spike_latency_ms=500
        )

    def test_custom_spike_latency(self) -> None:
        """Custom spike_latency_ms is passed through."""
        mock_tc = _make_mock_tc()

        uc.inject_latency_spike(mock_tc, duration_ms=1500, spike_latency_ms=1000)

        mock_tc.inject_transient.assert_called_once_with(
            "latency_spike", 1500, spike_latency_ms=1000
        )

    def test_event_type_is_latency_spike(self) -> None:
        """Event type passed to inject_transient is 'latency_spike'."""
        mock_tc = _make_mock_tc()

        uc.inject_latency_spike(mock_tc, duration_ms=500)

        assert mock_tc.inject_transient.call_args[0][0] == "latency_spike"


# ---------------------------------------------------------------------------
# inject_packet_storm()
# ---------------------------------------------------------------------------


class TestInjectPacketStorm:
    """Tests for inject_packet_storm()."""

    def test_default_loss_percent(self) -> None:
        """Default loss_percent=10.0."""
        mock_tc = _make_mock_tc()

        uc.inject_packet_storm(mock_tc, duration_ms=2000)

        mock_tc.inject_transient.assert_called_once_with(
            "packet_storm", 2000, loss_percent=10.0
        )

    def test_custom_loss_percent(self) -> None:
        """Custom loss_percent is passed through."""
        mock_tc = _make_mock_tc()

        uc.inject_packet_storm(mock_tc, duration_ms=3000, loss_percent=25.0)

        mock_tc.inject_transient.assert_called_once_with(
            "packet_storm", 3000, loss_percent=25.0
        )

    def test_event_type_is_packet_storm(self) -> None:
        """Event type passed to inject_transient is 'packet_storm'."""
        mock_tc = _make_mock_tc()

        uc.inject_packet_storm(mock_tc, duration_ms=500)

        assert mock_tc.inject_transient.call_args[0][0] == "packet_storm"
