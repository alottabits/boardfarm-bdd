"""Unit tests for boardfarm3.use_cases.qoe and boardfarm3.lib.qoe.

Tests the use-case and library layers in complete isolation using ``unittest.mock``.
No boardfarm infrastructure, no running containers, and no network access are required.
Every dependency on the device manager, devices, and boardfarm config is replaced by
``MagicMock`` / ``patch``.

Run without any boardfarm flags:

    pytest tests/bf_use_cases/test_qoe_use_cases.py -v

Coverage:
- ``calculate_mos()``               — E-model math correctness, boundary values
- ``QoEResult``                    — dataclass defaults and field isolation
- ``get_qoe_client()``             — device selection, single/multi, error paths
- ``measure_productivity()``        — thin wrapper delegation
- ``measure_streaming()``           — thin wrapper delegation
- ``measure_conferencing()``        — thin wrapper delegation
- ``assert_productivity_slo()``     — pass and fail cases (TTFB + load time)
- ``assert_streaming_slo()``        — pass and fail cases (startup + rebuffer)
- ``assert_conferencing_slo()``     — pass and fail cases (MOS + per-metric)
- ``assert_request_allowed()``      — success=True passes, success=False raises
- ``assert_request_blocked()``      — success=False passes, success=True raises
- ``assert_connection_allowed()``   — connected=True passes, False raises
- ``assert_connection_blocked()``   — connected=False passes, True raises
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from boardfarm3.exceptions import DeviceNotFound
from boardfarm3.lib.qoe import QoEResult, calculate_mos
from boardfarm3.templates.qoe_client import QoEClient
from boardfarm3.use_cases import qoe as uc


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_client() -> MagicMock:
    """Return a MagicMock with the QoEClient spec."""
    return MagicMock(spec=QoEClient)


def _make_productivity_result(
    *,
    ttfb_ms: float | None = 50.0,
    load_time_ms: float | None = 300.0,
    protocol: str | None = None,
    success: bool = True,
) -> QoEResult:
    return QoEResult(
        ttfb_ms=ttfb_ms,
        load_time_ms=load_time_ms,
        protocol=protocol,
        success=success,
    )


def _make_streaming_result(
    *,
    startup_time_ms: float | None = 800.0,
    rebuffer_ratio: float | None = 0.02,
    success: bool = True,
) -> QoEResult:
    return QoEResult(
        startup_time_ms=startup_time_ms,
        rebuffer_ratio=rebuffer_ratio,
        success=success,
    )


def _make_conferencing_result(
    *,
    latency_ms: float | None = 30.0,
    jitter_ms: float | None = 5.0,
    packet_loss_pct: float | None = 0.5,
    mos_score: float | None = 4.0,
    success: bool = True,
) -> QoEResult:
    return QoEResult(
        latency_ms=latency_ms,
        jitter_ms=jitter_ms,
        packet_loss_pct=packet_loss_pct,
        mos_score=mos_score,
        success=success,
    )


# ---------------------------------------------------------------------------
# QoEResult dataclass
# ---------------------------------------------------------------------------


class TestQoEResult:
    """Tests for QoEResult dataclass defaults and field isolation."""

    def test_defaults_all_none_except_success(self) -> None:
        """Default QoEResult has all metric fields None and success=True."""
        r = QoEResult()
        assert r.ttfb_ms is None
        assert r.load_time_ms is None
        assert r.startup_time_ms is None
        assert r.rebuffer_ratio is None
        assert r.latency_ms is None
        assert r.jitter_ms is None
        assert r.packet_loss_pct is None
        assert r.mos_score is None
        assert r.protocol is None
        assert r.success is True

    def test_productivity_fields_isolated(self) -> None:
        """Setting productivity fields does not affect streaming/conferencing fields."""
        r = QoEResult(ttfb_ms=50.0, load_time_ms=300.0)
        assert r.startup_time_ms is None
        assert r.rebuffer_ratio is None
        assert r.latency_ms is None
        assert r.mos_score is None

    def test_streaming_fields_isolated(self) -> None:
        """Setting streaming fields does not affect productivity/conferencing fields."""
        r = QoEResult(startup_time_ms=800.0, rebuffer_ratio=0.01)
        assert r.ttfb_ms is None
        assert r.load_time_ms is None
        assert r.latency_ms is None
        assert r.mos_score is None

    def test_success_can_be_false(self) -> None:
        """success=False is a valid explicit value."""
        r = QoEResult(success=False)
        assert r.success is False

    def test_protocol_field(self) -> None:
        """protocol field accepts None and valid HTTP version strings."""
        assert QoEResult().protocol is None
        assert QoEResult(protocol="h2").protocol == "h2"
        assert QoEResult(protocol="h3").protocol == "h3"
        assert QoEResult(protocol="http/1.1").protocol == "http/1.1"


# ---------------------------------------------------------------------------
# calculate_mos()
# ---------------------------------------------------------------------------


class TestCalculateMos:
    """Tests for the ITU-T G.107 E-model MOS calculation."""

    def test_ideal_conditions_return_high_mos(self) -> None:
        """Ideal conditions (0ms latency/jitter, 0% loss) produce MOS near 4.4."""
        mos = calculate_mos(latency_ms=0, jitter_ms=0, loss_percent=0.0)
        assert mos >= 4.0, f"Expected MOS >= 4.0 for ideal conditions, got {mos}"

    def test_high_loss_reduces_mos(self) -> None:
        """Significant packet loss (10%) reduces MOS below 3.5 (below "good quality")."""
        mos = calculate_mos(latency_ms=20, jitter_ms=5, loss_percent=10.0)
        assert mos < 3.5, f"Expected MOS < 3.5 for 10% loss, got {mos}"

    def test_very_high_loss_reduces_mos_below_3(self) -> None:
        """Very high packet loss (20%) reduces MOS below 3.0."""
        mos = calculate_mos(latency_ms=20, jitter_ms=5, loss_percent=20.0)
        assert mos < 3.0, f"Expected MOS < 3.0 for 20% loss, got {mos}"

    def test_high_latency_reduces_mos(self) -> None:
        """High latency (600ms satellite) reduces MOS below 3.5."""
        mos = calculate_mos(latency_ms=600, jitter_ms=50, loss_percent=2.0)
        assert mos < 3.5, f"Expected MOS < 3.5 for satellite latency, got {mos}"

    def test_mos_clamped_to_lower_bound(self) -> None:
        """Extreme impairment cannot push MOS below 1.0."""
        mos = calculate_mos(latency_ms=5000, jitter_ms=1000, loss_percent=99.9)
        assert mos >= 1.0, f"MOS below 1.0: {mos}"

    def test_mos_clamped_to_upper_bound(self) -> None:
        """Perfect conditions cannot push MOS above 4.5."""
        mos = calculate_mos(latency_ms=0, jitter_ms=0, loss_percent=0.0)
        assert mos <= 4.5, f"MOS above 4.5: {mos}"

    def test_mos_monotonically_decreasing_with_loss(self) -> None:
        """MOS decreases monotonically as packet loss increases."""
        loss_values = [0.0, 0.5, 1.0, 2.0, 5.0, 10.0]
        scores = [calculate_mos(20, 5, loss) for loss in loss_values]
        for i in range(1, len(scores)):
            assert scores[i] <= scores[i - 1], (
                f"MOS did not decrease: loss {loss_values[i-1]}% → {scores[i-1]:.3f}, "
                f"loss {loss_values[i]}% → {scores[i]:.3f}"
            )

    def test_mos_monotonically_decreasing_with_latency(self) -> None:
        """MOS decreases monotonically as latency increases."""
        latencies = [0, 50, 100, 200, 400, 600]
        scores = [calculate_mos(lat, 0, 0.0) for lat in latencies]
        for i in range(1, len(scores)):
            assert scores[i] <= scores[i - 1], (
                f"MOS did not decrease: latency {latencies[i-1]}ms → {scores[i-1]:.3f}, "
                f"latency {latencies[i]}ms → {scores[i]:.3f}"
            )

    def test_mos_cable_typical_is_good(self) -> None:
        """Cable typical (15ms, 5ms jitter, 0.1% loss) yields MOS > 3.8."""
        mos = calculate_mos(latency_ms=15, jitter_ms=5, loss_percent=0.1)
        assert mos > 3.8, (
            f"Expected MOS > 3.8 for cable_typical conditions, got {mos}"
        )

    def test_mos_returns_float(self) -> None:
        """calculate_mos always returns a float."""
        mos = calculate_mos(latency_ms=20, jitter_ms=5, loss_percent=0.5)
        assert isinstance(mos, float), f"Expected float, got {type(mos)}"

    def test_mos_zero_loss_special_path(self) -> None:
        """Zero packet loss takes a special path (no Bpl division); verify stable."""
        mos_zero = calculate_mos(latency_ms=20, jitter_ms=5, loss_percent=0.0)
        mos_tiny = calculate_mos(latency_ms=20, jitter_ms=5, loss_percent=0.001)
        assert abs(mos_zero - mos_tiny) < 0.1, (
            f"MOS jump between 0% and 0.001% loss: {mos_zero} vs {mos_tiny}"
        )


# ---------------------------------------------------------------------------
# get_qoe_client()
# ---------------------------------------------------------------------------


class TestGetQoEClient:
    """Tests for get_qoe_client() device selection logic."""

    @patch("boardfarm3.use_cases.qoe.get_device_manager")
    def test_single_device_no_name(self, mock_gdm: MagicMock) -> None:
        """Returns the sole QoEClient when exactly one device is registered and name=None."""
        mock_client = _make_mock_client()
        mock_gdm.return_value.get_devices_by_type.return_value = {
            "lan_qoe_client": mock_client
        }
        result = uc.get_qoe_client()
        assert result is mock_client

    @patch("boardfarm3.use_cases.qoe.get_device_manager")
    def test_named_device_found(self, mock_gdm: MagicMock) -> None:
        """Returns the named device when name matches an available QoEClient."""
        mock_client = _make_mock_client()
        mock_gdm.return_value.get_devices_by_type.return_value = {
            "lan_qoe_client": mock_client
        }
        result = uc.get_qoe_client("lan_qoe_client")
        assert result is mock_client

    @patch("boardfarm3.use_cases.qoe.get_device_manager")
    def test_named_device_not_found_raises(self, mock_gdm: MagicMock) -> None:
        """Raises DeviceNotFound when a specified name is not registered."""
        mock_gdm.return_value.get_devices_by_type.return_value = {
            "lan_qoe_client": _make_mock_client()
        }
        with pytest.raises(DeviceNotFound, match="nonexistent"):
            uc.get_qoe_client("nonexistent")

    @patch("boardfarm3.use_cases.qoe.get_device_manager")
    def test_no_devices_raises(self, mock_gdm: MagicMock) -> None:
        """Raises DeviceNotFound when no QoEClient is registered."""
        mock_gdm.return_value.get_devices_by_type.return_value = {}
        with pytest.raises(DeviceNotFound, match="No QoEClient"):
            uc.get_qoe_client()

    @patch("boardfarm3.use_cases.qoe.get_device_manager")
    def test_multiple_devices_no_name_raises(self, mock_gdm: MagicMock) -> None:
        """Raises ValueError when multiple QoEClients exist and no name is specified."""
        mock_gdm.return_value.get_devices_by_type.return_value = {
            "lan_qoe_client_1": _make_mock_client(),
            "lan_qoe_client_2": _make_mock_client(),
        }
        with pytest.raises(ValueError, match="Multiple QoEClient"):
            uc.get_qoe_client()

    @patch("boardfarm3.use_cases.qoe.get_device_manager")
    def test_multiple_devices_named_returns_correct(self, mock_gdm: MagicMock) -> None:
        """Returns the correct device when multiple QoEClients exist and name is given."""
        mock_c1 = _make_mock_client()
        mock_c2 = _make_mock_client()
        mock_gdm.return_value.get_devices_by_type.return_value = {
            "lan_qoe_client_1": mock_c1,
            "lan_qoe_client_2": mock_c2,
        }
        assert uc.get_qoe_client("lan_qoe_client_1") is mock_c1
        assert uc.get_qoe_client("lan_qoe_client_2") is mock_c2


# ---------------------------------------------------------------------------
# measure_productivity() / measure_streaming() / measure_conferencing() — wrappers
# ---------------------------------------------------------------------------


class TestMeasurementWrappers:
    """Tests for the thin measurement wrapper functions."""

    def test_measure_productivity_delegates(self) -> None:
        """measure_productivity() calls client.measure_productivity() with correct args."""
        client = _make_mock_client()
        expected = _make_productivity_result()
        client.measure_productivity.return_value = expected

        result = uc.measure_productivity(client, "http://example.com/", scenario="page_load")

        client.measure_productivity.assert_called_once_with(
            "http://example.com/", scenario="page_load"
        )
        assert result is expected

    def test_measure_productivity_default_scenario(self) -> None:
        """measure_productivity() passes default scenario='page_load'."""
        client = _make_mock_client()
        client.measure_productivity.return_value = _make_productivity_result()

        uc.measure_productivity(client, "http://example.com/")

        client.measure_productivity.assert_called_once_with(
            "http://example.com/", scenario="page_load"
        )

    def test_measure_streaming_delegates(self) -> None:
        """measure_streaming() calls client.measure_streaming() with correct args."""
        client = _make_mock_client()
        expected = _make_streaming_result()
        client.measure_streaming.return_value = expected

        result = uc.measure_streaming(client, "http://example.com/stream.m3u8", duration_s=45)

        client.measure_streaming.assert_called_once_with(
            "http://example.com/stream.m3u8", duration_s=45
        )
        assert result is expected

    def test_measure_streaming_default_duration(self) -> None:
        """measure_streaming() passes default duration_s=30."""
        client = _make_mock_client()
        client.measure_streaming.return_value = _make_streaming_result()

        uc.measure_streaming(client, "http://example.com/stream.m3u8")

        client.measure_streaming.assert_called_once_with(
            "http://example.com/stream.m3u8", duration_s=30
        )

    def test_measure_conferencing_delegates(self) -> None:
        """measure_conferencing() calls client.measure_conferencing() with correct args."""
        client = _make_mock_client()
        expected = _make_conferencing_result()
        client.measure_conferencing.return_value = expected

        result = uc.measure_conferencing(client, "ws://conf.internal/session", duration_s=30)

        client.measure_conferencing.assert_called_once_with(
            "ws://conf.internal/session", duration_s=30
        )
        assert result is expected

    def test_measure_conferencing_default_duration(self) -> None:
        """measure_conferencing() passes default duration_s=60."""
        client = _make_mock_client()
        client.measure_conferencing.return_value = _make_conferencing_result()

        uc.measure_conferencing(client, "ws://conf.internal/session")

        client.measure_conferencing.assert_called_once_with(
            "ws://conf.internal/session", duration_s=60
        )


# ---------------------------------------------------------------------------
# assert_productivity_slo()
# ---------------------------------------------------------------------------


class TestAssertProductivitySlo:
    """Tests for assert_productivity_slo() — pass and fail paths."""

    def test_passes_when_ttfb_within_threshold(self) -> None:
        """No assertion raised when TTFB is below max_ttfb_ms."""
        result = _make_productivity_result(ttfb_ms=50.0)
        uc.assert_productivity_slo(result, max_ttfb_ms=100.0)

    def test_fails_when_ttfb_exceeds_threshold(self) -> None:
        """AssertionError raised when TTFB exceeds max_ttfb_ms."""
        result = _make_productivity_result(ttfb_ms=150.0)
        with pytest.raises(AssertionError, match="TTFB SLO violation"):
            uc.assert_productivity_slo(result, max_ttfb_ms=100.0)

    def test_passes_when_load_time_within_threshold(self) -> None:
        """No assertion raised when load time is below max_load_time_ms."""
        result = _make_productivity_result(load_time_ms=500.0)
        uc.assert_productivity_slo(result, max_load_time_ms=1000.0)

    def test_fails_when_load_time_exceeds_threshold(self) -> None:
        """AssertionError raised when load time exceeds max_load_time_ms."""
        result = _make_productivity_result(load_time_ms=1500.0)
        with pytest.raises(AssertionError, match="Page load time SLO violation"):
            uc.assert_productivity_slo(result, max_load_time_ms=1000.0)

    def test_fails_when_success_is_false(self) -> None:
        """AssertionError raised immediately when result.success is False."""
        result = _make_productivity_result(success=False)
        with pytest.raises(AssertionError, match="success=False"):
            uc.assert_productivity_slo(result, max_ttfb_ms=100.0)

    def test_fails_when_ttfb_is_none_and_threshold_set(self) -> None:
        """AssertionError raised when ttfb_ms is None but max_ttfb_ms is set."""
        result = _make_productivity_result(ttfb_ms=None)
        with pytest.raises(AssertionError, match="ttfb_ms is None"):
            uc.assert_productivity_slo(result, max_ttfb_ms=100.0)

    def test_fails_when_load_time_is_none_and_threshold_set(self) -> None:
        """AssertionError raised when load_time_ms is None but max_load_time_ms is set."""
        result = _make_productivity_result(load_time_ms=None)
        with pytest.raises(AssertionError, match="load_time_ms is None"):
            uc.assert_productivity_slo(result, max_load_time_ms=1000.0)

    def test_passes_when_both_thresholds_satisfied(self) -> None:
        """No assertion raised when both TTFB and load time are within bounds."""
        result = _make_productivity_result(ttfb_ms=60.0, load_time_ms=400.0)
        uc.assert_productivity_slo(result, max_ttfb_ms=100.0, max_load_time_ms=1000.0)

    def test_label_appears_in_error_message(self) -> None:
        """Assertion error message includes the label when provided."""
        result = _make_productivity_result(ttfb_ms=200.0)
        with pytest.raises(AssertionError, match=r"\[cable_typical\]"):
            uc.assert_productivity_slo(result, max_ttfb_ms=100.0, label="cable_typical")

    def test_passes_exactly_at_threshold(self) -> None:
        """TTFB exactly equal to max_ttfb_ms does not raise."""
        result = _make_productivity_result(ttfb_ms=100.0)
        uc.assert_productivity_slo(result, max_ttfb_ms=100.0)


# ---------------------------------------------------------------------------
# assert_streaming_slo()
# ---------------------------------------------------------------------------


class TestAssertStreamingSlo:
    """Tests for assert_streaming_slo() — pass and fail paths."""

    def test_passes_startup_within_threshold(self) -> None:
        """No assertion raised when startup_time_ms is within max_startup_time_ms."""
        result = _make_streaming_result(startup_time_ms=800.0)
        uc.assert_streaming_slo(result, max_startup_time_ms=2000.0)

    def test_fails_startup_exceeds_threshold(self) -> None:
        """AssertionError raised when startup_time_ms exceeds max_startup_time_ms."""
        result = _make_streaming_result(startup_time_ms=3000.0)
        with pytest.raises(AssertionError, match="Streaming startup SLO violation"):
            uc.assert_streaming_slo(result, max_startup_time_ms=2000.0)

    def test_passes_rebuffer_within_threshold(self) -> None:
        """No assertion raised when rebuffer_ratio is within max_rebuffer_ratio."""
        result = _make_streaming_result(rebuffer_ratio=0.01)
        uc.assert_streaming_slo(result, max_rebuffer_ratio=0.05)

    def test_fails_rebuffer_exceeds_threshold(self) -> None:
        """AssertionError raised when rebuffer_ratio exceeds max_rebuffer_ratio."""
        result = _make_streaming_result(rebuffer_ratio=0.10)
        with pytest.raises(AssertionError, match="Rebuffer ratio SLO violation"):
            uc.assert_streaming_slo(result, max_rebuffer_ratio=0.05)

    def test_fails_when_success_is_false(self) -> None:
        """AssertionError raised immediately when result.success is False."""
        result = _make_streaming_result(success=False)
        with pytest.raises(AssertionError, match="success=False"):
            uc.assert_streaming_slo(result, max_startup_time_ms=2000.0)

    def test_fails_when_startup_is_none_and_threshold_set(self) -> None:
        """AssertionError raised when startup_time_ms is None but threshold is set."""
        result = _make_streaming_result(startup_time_ms=None)
        with pytest.raises(AssertionError, match="startup_time_ms is None"):
            uc.assert_streaming_slo(result, max_startup_time_ms=2000.0)

    def test_phase1_rebuffer_zero_passes_threshold(self) -> None:
        """Phase 1 rebuffer_ratio=0.0 passes any max_rebuffer_ratio >= 0."""
        result = _make_streaming_result(rebuffer_ratio=0.0)
        uc.assert_streaming_slo(result, max_rebuffer_ratio=0.05)

    def test_label_appears_in_error_message(self) -> None:
        """Assertion error message includes the label when provided."""
        result = _make_streaming_result(startup_time_ms=5000.0)
        with pytest.raises(AssertionError, match=r"\[4g_mobile\]"):
            uc.assert_streaming_slo(result, max_startup_time_ms=2000.0, label="4g_mobile")


# ---------------------------------------------------------------------------
# assert_conferencing_slo()
# ---------------------------------------------------------------------------


class TestAssertConferencingSlo:
    """Tests for assert_conferencing_slo() — pass and fail paths."""

    def test_passes_when_mos_above_threshold(self) -> None:
        """No assertion raised when MOS is above min_mos."""
        result = _make_conferencing_result(mos_score=4.0)
        uc.assert_conferencing_slo(result, min_mos=3.5)

    def test_fails_when_mos_below_threshold(self) -> None:
        """AssertionError raised when MOS is below min_mos."""
        result = _make_conferencing_result(mos_score=2.8)
        with pytest.raises(AssertionError, match="MOS SLO violation"):
            uc.assert_conferencing_slo(result, min_mos=3.5)

    def test_default_min_mos_is_3_5(self) -> None:
        """Default min_mos=3.5 is enforced when not explicitly provided."""
        result_pass = _make_conferencing_result(mos_score=3.6)
        uc.assert_conferencing_slo(result_pass)

        result_fail = _make_conferencing_result(mos_score=3.4)
        with pytest.raises(AssertionError, match="MOS SLO violation"):
            uc.assert_conferencing_slo(result_fail)

    def test_fails_when_success_is_false(self) -> None:
        """AssertionError raised immediately when result.success is False."""
        result = _make_conferencing_result(success=False)
        with pytest.raises(AssertionError, match="success=False"):
            uc.assert_conferencing_slo(result)

    def test_fails_when_mos_is_none(self) -> None:
        """AssertionError raised when mos_score is None."""
        result = _make_conferencing_result(mos_score=None)
        with pytest.raises(AssertionError, match="MOS not calculated"):
            uc.assert_conferencing_slo(result)

    def test_passes_with_latency_threshold(self) -> None:
        """No assertion raised when latency is within max_latency_ms."""
        result = _make_conferencing_result(mos_score=4.0, latency_ms=30.0)
        uc.assert_conferencing_slo(result, max_latency_ms=100.0)

    def test_fails_with_latency_threshold_exceeded(self) -> None:
        """AssertionError raised when latency exceeds max_latency_ms."""
        result = _make_conferencing_result(mos_score=4.0, latency_ms=150.0)
        with pytest.raises(AssertionError, match="latency SLO violation"):
            uc.assert_conferencing_slo(result, max_latency_ms=100.0)

    def test_passes_with_jitter_threshold(self) -> None:
        """No assertion raised when jitter is within max_jitter_ms."""
        result = _make_conferencing_result(mos_score=4.0, jitter_ms=5.0)
        uc.assert_conferencing_slo(result, max_jitter_ms=30.0)

    def test_fails_with_jitter_threshold_exceeded(self) -> None:
        """AssertionError raised when jitter exceeds max_jitter_ms."""
        result = _make_conferencing_result(mos_score=4.0, jitter_ms=50.0)
        with pytest.raises(AssertionError, match="jitter SLO violation"):
            uc.assert_conferencing_slo(result, max_jitter_ms=30.0)

    def test_passes_with_loss_threshold(self) -> None:
        """No assertion raised when packet loss is within max_packet_loss_pct."""
        result = _make_conferencing_result(mos_score=4.0, packet_loss_pct=0.5)
        uc.assert_conferencing_slo(result, max_packet_loss_pct=2.0)

    def test_fails_with_loss_threshold_exceeded(self) -> None:
        """AssertionError raised when packet loss exceeds max_packet_loss_pct."""
        result = _make_conferencing_result(mos_score=4.0, packet_loss_pct=3.0)
        with pytest.raises(AssertionError, match="packet-loss SLO violation"):
            uc.assert_conferencing_slo(result, max_packet_loss_pct=2.0)

    def test_label_appears_in_error_message(self) -> None:
        """Assertion error message includes the label when provided."""
        result = _make_conferencing_result(mos_score=2.5)
        with pytest.raises(AssertionError, match=r"\[satellite\]"):
            uc.assert_conferencing_slo(result, min_mos=3.5, label="satellite")


# ---------------------------------------------------------------------------
# assert_request_allowed() / assert_request_blocked()
# ---------------------------------------------------------------------------


class TestAssertRequestAllowedBlocked:
    """Tests for security assertion helpers on QoEResult.success."""

    def test_assert_request_allowed_passes_on_success(self) -> None:
        """assert_request_allowed() passes when result.success is True."""
        result = QoEResult(success=True)
        uc.assert_request_allowed(result)

    def test_assert_request_allowed_fails_on_blocked(self) -> None:
        """assert_request_allowed() raises AssertionError when result.success is False."""
        result = QoEResult(success=False)
        with pytest.raises(AssertionError, match="unexpectedly blocked"):
            uc.assert_request_allowed(result)

    def test_assert_request_blocked_passes_on_failure(self) -> None:
        """assert_request_blocked() passes when result.success is False."""
        result = QoEResult(success=False)
        uc.assert_request_blocked(result)

    def test_assert_request_blocked_fails_on_allowed(self) -> None:
        """assert_request_blocked() raises AssertionError when result.success is True."""
        result = QoEResult(success=True)
        with pytest.raises(AssertionError, match="unexpectedly allowed"):
            uc.assert_request_blocked(result)

    def test_assert_request_allowed_label_in_message(self) -> None:
        """Label appears in error message for assert_request_allowed."""
        result = QoEResult(success=False)
        with pytest.raises(AssertionError, match=r"\[eicar_download\]"):
            uc.assert_request_allowed(result, label="eicar_download")

    def test_assert_request_blocked_label_in_message(self) -> None:
        """Label appears in error message for assert_request_blocked."""
        result = QoEResult(success=True)
        with pytest.raises(AssertionError, match=r"\[c2_callback\]"):
            uc.assert_request_blocked(result, label="c2_callback")


# ---------------------------------------------------------------------------
# assert_connection_allowed() / assert_connection_blocked()
# ---------------------------------------------------------------------------


class TestAssertConnectionAllowedBlocked:
    """Tests for TCP connection security assertion helpers."""

    def test_assert_connection_allowed_passes_when_connected(self) -> None:
        """assert_connection_allowed() passes when attempt_outbound_connection returns True."""
        client = _make_mock_client()
        client.attempt_outbound_connection.return_value = True

        uc.assert_connection_allowed(client, "172.16.0.10", 8080)

        client.attempt_outbound_connection.assert_called_once_with(
            "172.16.0.10", 8080, timeout_s=5.0
        )

    def test_assert_connection_allowed_fails_when_blocked(self) -> None:
        """assert_connection_allowed() raises AssertionError when connection fails."""
        client = _make_mock_client()
        client.attempt_outbound_connection.return_value = False

        with pytest.raises(AssertionError, match="unexpectedly blocked"):
            uc.assert_connection_allowed(client, "172.16.0.10", 8080)

    def test_assert_connection_blocked_passes_when_blocked(self) -> None:
        """assert_connection_blocked() passes when attempt_outbound_connection returns False."""
        client = _make_mock_client()
        client.attempt_outbound_connection.return_value = False

        uc.assert_connection_blocked(client, "172.16.0.20", 4444)

        client.attempt_outbound_connection.assert_called_once_with(
            "172.16.0.20", 4444, timeout_s=5.0
        )

    def test_assert_connection_blocked_fails_when_allowed(self) -> None:
        """assert_connection_blocked() raises AssertionError when connection succeeds."""
        client = _make_mock_client()
        client.attempt_outbound_connection.return_value = True

        with pytest.raises(AssertionError, match="unexpectedly allowed"):
            uc.assert_connection_blocked(client, "172.16.0.20", 4444)

    def test_assert_connection_allowed_custom_timeout(self) -> None:
        """assert_connection_allowed() passes custom timeout_s to the device method."""
        client = _make_mock_client()
        client.attempt_outbound_connection.return_value = True

        uc.assert_connection_allowed(client, "172.16.0.10", 8080, timeout_s=10.0)

        client.attempt_outbound_connection.assert_called_once_with(
            "172.16.0.10", 8080, timeout_s=10.0
        )

    def test_assert_connection_blocked_custom_timeout(self) -> None:
        """assert_connection_blocked() passes custom timeout_s to the device method."""
        client = _make_mock_client()
        client.attempt_outbound_connection.return_value = False

        uc.assert_connection_blocked(client, "10.0.0.1", 22, timeout_s=3.0)

        client.attempt_outbound_connection.assert_called_once_with(
            "10.0.0.1", 22, timeout_s=3.0
        )

    def test_assert_connection_allowed_label_in_message(self) -> None:
        """Label appears in error message for assert_connection_allowed."""
        client = _make_mock_client()
        client.attempt_outbound_connection.return_value = False

        with pytest.raises(AssertionError, match=r"\[port_80_should_be_open\]"):
            uc.assert_connection_allowed(
                client, "172.16.0.10", 8080, label="port_80_should_be_open"
            )

    def test_assert_connection_blocked_label_in_message(self) -> None:
        """Label appears in error message for assert_connection_blocked."""
        client = _make_mock_client()
        client.attempt_outbound_connection.return_value = True

        with pytest.raises(AssertionError, match=r"\[c2_port_blocked\]"):
            uc.assert_connection_blocked(
                client, "172.16.0.20", 4444, label="c2_port_blocked"
            )
