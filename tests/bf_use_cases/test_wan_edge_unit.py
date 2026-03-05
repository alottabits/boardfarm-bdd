"""Unit tests for boardfarm3.use_cases.wan_edge.

Tests the use-case layer in complete isolation using ``unittest.mock``.
No boardfarm infrastructure, no running containers, and no network access are required.
Every dependency on the device manager and devices is replaced by ``MagicMock`` / ``patch``.

Run without any boardfarm flags:

    pytest tests/bf_use_cases/test_wan_edge_unit.py -v

Coverage:
- ``get_wan_edge()``                      — device selection, single/multi, error paths
- ``assert_active_path()``                — pass (correct WAN) and fail (wrong WAN) cases
- ``assert_path_steers_on_impairment()``  — steers to correct fallback, times out, wrong path
- ``assert_policy_steered_path()``        — policy applied, correct path, wrong path
- ``assert_wan_interface_status()``       — up/down/degraded pass/fail, missing label
- ``assert_path_metrics_within_slo()``    — latency/jitter/loss pass and fail, partial
- ``measure_failover_convergence()``      — returns convergence time, timeout raises
- ``assert_failover_time()``              — within SLO passes, exceeded fails
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from boardfarm3.exceptions import DeviceNotFound
from boardfarm3.templates.traffic_controller import TrafficController
from boardfarm3.templates.wan_edge import LinkStatus, PathMetrics, WANEdgeDevice
from boardfarm3.use_cases import wan_edge as uc


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_dut() -> MagicMock:
    """Return a MagicMock with the WANEdgeDevice spec."""
    return MagicMock(spec=WANEdgeDevice)


def _make_mock_tc() -> MagicMock:
    """Return a MagicMock with the TrafficController spec."""
    return MagicMock(spec=TrafficController)


def _make_link_status(name: str, state: str, ip: str = "10.0.0.1") -> LinkStatus:
    return LinkStatus(name=name, state=state, ip_address=ip)


def _make_path_metrics(
    latency_ms: float = 10.0,
    jitter_ms: float = 2.0,
    loss_percent: float = 0.1,
    link_name: str = "wan1",
) -> PathMetrics:
    return PathMetrics(
        latency_ms=latency_ms,
        jitter_ms=jitter_ms,
        loss_percent=loss_percent,
        link_name=link_name,
    )


# ---------------------------------------------------------------------------
# get_wan_edge()
# ---------------------------------------------------------------------------


class TestGetWanEdge:
    """Tests for get_wan_edge() device selection logic."""

    @patch("boardfarm3.use_cases.wan_edge.get_device_manager")
    def test_single_device_no_name(self, mock_gdm: MagicMock) -> None:
        """Returns the sole WANEdgeDevice when exactly one is registered and name=None."""
        mock_dut = _make_mock_dut()
        mock_gdm.return_value.get_devices_by_type.return_value = {"sdwan": mock_dut}
        result = uc.get_wan_edge()
        assert result is mock_dut

    @patch("boardfarm3.use_cases.wan_edge.get_device_manager")
    def test_single_device_with_matching_name(self, mock_gdm: MagicMock) -> None:
        """Selects by name when exactly one device matches the specified name."""
        mock_dut = _make_mock_dut()
        mock_gdm.return_value.get_devices_by_type.return_value = {"sdwan": mock_dut}
        result = uc.get_wan_edge("sdwan")
        assert result is mock_dut

    @patch("boardfarm3.use_cases.wan_edge.get_device_manager")
    def test_multi_device_with_name(self, mock_gdm: MagicMock) -> None:
        """Selects the correct device when multiple are registered and name is given."""
        dut1 = _make_mock_dut()
        dut2 = _make_mock_dut()
        mock_gdm.return_value.get_devices_by_type.return_value = {
            "sdwan": dut1,
            "sdwan2": dut2,
        }
        assert uc.get_wan_edge("sdwan") is dut1
        assert uc.get_wan_edge("sdwan2") is dut2

    @patch("boardfarm3.use_cases.wan_edge.get_device_manager")
    def test_multi_device_no_name_raises_value_error(self, mock_gdm: MagicMock) -> None:
        """Raises ValueError when multiple WANEdgeDevices exist and name is omitted."""
        mock_gdm.return_value.get_devices_by_type.return_value = {
            "sdwan": _make_mock_dut(),
            "sdwan2": _make_mock_dut(),
        }
        with pytest.raises(ValueError, match="Multiple WANEdgeDevice"):
            uc.get_wan_edge()

    @patch("boardfarm3.use_cases.wan_edge.get_device_manager")
    def test_no_devices_raises_device_not_found(self, mock_gdm: MagicMock) -> None:
        """Raises DeviceNotFound when no WANEdgeDevice devices are registered."""
        mock_gdm.return_value.get_devices_by_type.return_value = {}
        with pytest.raises(DeviceNotFound, match="No WANEdgeDevice"):
            uc.get_wan_edge()

    @patch("boardfarm3.use_cases.wan_edge.get_device_manager")
    def test_named_device_not_found_raises_device_not_found(
        self, mock_gdm: MagicMock
    ) -> None:
        """Raises DeviceNotFound when the specified name does not match any device."""
        mock_gdm.return_value.get_devices_by_type.return_value = {
            "sdwan": _make_mock_dut()
        }
        with pytest.raises(DeviceNotFound, match="not found"):
            uc.get_wan_edge("no_such_dut")


# ---------------------------------------------------------------------------
# assert_active_path()
# ---------------------------------------------------------------------------


class TestAssertActivePath:
    """Tests for assert_active_path()."""

    def test_pass_when_active_matches_expected(self) -> None:
        """No exception when DUT reports the expected WAN label as active."""
        dut = _make_mock_dut()
        dut.get_active_wan_interface.return_value = "wan1"
        uc.assert_active_path(dut, expected_wan="wan1")
        dut.get_active_wan_interface.assert_called_once_with(flow_dst=None)

    def test_pass_with_flow_dst(self) -> None:
        """flow_dst is forwarded to get_active_wan_interface."""
        dut = _make_mock_dut()
        dut.get_active_wan_interface.return_value = "wan2"
        uc.assert_active_path(dut, expected_wan="wan2", flow_dst="172.16.0.11")
        dut.get_active_wan_interface.assert_called_once_with(flow_dst="172.16.0.11")

    def test_fail_when_active_mismatches(self) -> None:
        """AssertionError raised when DUT reports a different WAN than expected."""
        dut = _make_mock_dut()
        dut.get_active_wan_interface.return_value = "wan2"
        with pytest.raises(AssertionError, match="Expected active path 'wan1'"):
            uc.assert_active_path(dut, expected_wan="wan1")

    def test_assertion_message_includes_label(self) -> None:
        """Label is included in the assertion message when provided."""
        dut = _make_mock_dut()
        dut.get_active_wan_interface.return_value = "wan2"
        with pytest.raises(AssertionError, match=r"\[scenario-42\]"):
            uc.assert_active_path(dut, expected_wan="wan1", label="scenario-42")


# ---------------------------------------------------------------------------
# assert_path_steers_on_impairment()
# ---------------------------------------------------------------------------


class TestAssertPathSteersOnImpairment:
    """Tests for assert_path_steers_on_impairment()."""

    @patch("boardfarm3.use_cases.wan_edge.tc_use_cases.inject_blackout")
    def test_steers_to_correct_fallback(self, mock_inject: MagicMock) -> None:
        """Passes when DUT switches from impaired WAN to expected fallback."""
        dut = _make_mock_dut()
        tc = _make_mock_tc()
        # First poll still on wan1, second on wan2
        dut.get_active_wan_interface.side_effect = ["wan1", "wan2"]
        uc.assert_path_steers_on_impairment(
            dut, tc, impaired_wan="wan1", expected_fallback_wan="wan2",
            poll_interval_ms=0,
        )
        mock_inject.assert_called_once()

    @patch("boardfarm3.use_cases.wan_edge.tc_use_cases.inject_blackout")
    def test_steers_immediately_on_first_poll(self, mock_inject: MagicMock) -> None:
        """Passes when DUT has already switched by the first poll.

        Verifies that inject_blackout is still called even when the DUT has
        already switched before the first poll — the impairment is injected
        first, then the result is observed.
        """
        dut = _make_mock_dut()
        tc = _make_mock_tc()
        dut.get_active_wan_interface.return_value = "wan2"
        uc.assert_path_steers_on_impairment(
            dut, tc, impaired_wan="wan1", expected_fallback_wan="wan2",
            poll_interval_ms=0,
        )
        mock_inject.assert_called_once()
        dut.get_active_wan_interface.assert_called()

    @patch("boardfarm3.use_cases.wan_edge.tc_use_cases.inject_blackout")
    def test_raises_when_steers_to_wrong_path(self, mock_inject: MagicMock) -> None:
        """AssertionError raised when DUT steers to a path other than expected fallback."""
        dut = _make_mock_dut()
        tc = _make_mock_tc()
        dut.get_active_wan_interface.side_effect = ["wan1", "wan3"]
        with pytest.raises(AssertionError, match="expected fallback 'wan2'"):
            uc.assert_path_steers_on_impairment(
                dut, tc, impaired_wan="wan1", expected_fallback_wan="wan2",
                poll_interval_ms=0,
            )

    @patch("boardfarm3.use_cases.wan_edge.tc_use_cases.inject_blackout")
    def test_raises_on_timeout(self, mock_inject: MagicMock) -> None:
        """AssertionError raised when DUT does not switch within timeout_ms."""
        dut = _make_mock_dut()
        tc = _make_mock_tc()
        # Always returns impaired wan — never switches
        dut.get_active_wan_interface.return_value = "wan1"
        with pytest.raises(AssertionError, match="did not steer away"):
            uc.assert_path_steers_on_impairment(
                dut, tc, impaired_wan="wan1", expected_fallback_wan="wan2",
                poll_interval_ms=0, timeout_ms=0,
            )

    @patch("boardfarm3.use_cases.wan_edge.tc_use_cases.inject_blackout")
    def test_assertion_includes_label(self, mock_inject: MagicMock) -> None:
        """Label is included in the assertion message on timeout."""
        dut = _make_mock_dut()
        tc = _make_mock_tc()
        dut.get_active_wan_interface.return_value = "wan1"
        with pytest.raises(AssertionError, match=r"\[test-label\]"):
            uc.assert_path_steers_on_impairment(
                dut, tc, impaired_wan="wan1", expected_fallback_wan="wan2",
                poll_interval_ms=0, timeout_ms=0, label="test-label",
            )

    @patch("boardfarm3.use_cases.wan_edge.tc_use_cases.inject_blackout")
    def test_inject_blackout_called_with_duration(self, mock_inject: MagicMock) -> None:
        """inject_blackout is called with the provided duration_ms."""
        dut = _make_mock_dut()
        tc = _make_mock_tc()
        dut.get_active_wan_interface.side_effect = ["wan1", "wan2"]
        uc.assert_path_steers_on_impairment(
            dut, tc, impaired_wan="wan1", expected_fallback_wan="wan2",
            duration_ms=5_000, poll_interval_ms=0,
        )
        mock_inject.assert_called_once_with(tc, duration_ms=5_000)


# ---------------------------------------------------------------------------
# assert_policy_steered_path()
# ---------------------------------------------------------------------------


class TestAssertPolicySteeeredPath:
    """Tests for assert_policy_steered_path()."""

    def test_pass_when_policy_steers_correctly(self) -> None:
        """No exception when DUT forwards the flow via expected WAN after policy applied."""
        dut = _make_mock_dut()
        dut.get_active_wan_interface.return_value = "wan2"
        policy = {"match": {"dscp": 34}, "action": {"prefer_wan": "wan2"}}
        uc.assert_policy_steered_path(dut, policy, flow_dst="172.16.0.11", expected_wan="wan2")
        dut.apply_policy.assert_called_once_with(policy)
        dut.get_active_wan_interface.assert_called_once_with(flow_dst="172.16.0.11")

    def test_fail_when_policy_does_not_steer_correctly(self) -> None:
        """AssertionError raised when DUT forwards via unexpected WAN after policy applied."""
        dut = _make_mock_dut()
        dut.get_active_wan_interface.return_value = "wan1"
        policy = {"match": {"dscp": 34}, "action": {"prefer_wan": "wan2"}}
        with pytest.raises(AssertionError, match="should steer"):
            uc.assert_policy_steered_path(
                dut, policy, flow_dst="172.16.0.11", expected_wan="wan2"
            )

    def test_assertion_includes_label(self) -> None:
        """Label is included in the assertion message on failure."""
        dut = _make_mock_dut()
        dut.get_active_wan_interface.return_value = "wan1"
        policy = {"action": {"prefer_wan": "wan2"}}
        with pytest.raises(AssertionError, match=r"\[pbr-test\]"):
            uc.assert_policy_steered_path(
                dut, policy, flow_dst="10.0.0.1", expected_wan="wan2", label="pbr-test"
            )

    def test_apply_policy_called_before_checking_path(self) -> None:
        """apply_policy is always called before get_active_wan_interface is read."""
        dut = _make_mock_dut()
        policy = {"action": {"prefer_wan": "wan2"}}
        call_order: list[str] = []

        def _apply(p: dict) -> None:
            call_order.append("apply")

        def _get_active(**kw: object) -> str:
            call_order.append("get")
            return "wan2"

        dut.apply_policy.side_effect = _apply
        dut.get_active_wan_interface.side_effect = _get_active
        uc.assert_policy_steered_path(dut, policy, flow_dst="10.0.0.1", expected_wan="wan2")
        assert call_order == ["apply", "get"]


# ---------------------------------------------------------------------------
# assert_wan_interface_status()
# ---------------------------------------------------------------------------


class TestAssertWanInterfaceStatus:
    """Tests for assert_wan_interface_status()."""

    def test_pass_when_state_matches(self) -> None:
        """Returns LinkStatus and does not raise when state matches expected."""
        dut = _make_mock_dut()
        dut.get_wan_interface_status.return_value = {
            "wan1": _make_link_status("wan1", "up"),
        }
        result = uc.assert_wan_interface_status(dut, "wan1", "up")
        assert isinstance(result, LinkStatus)
        assert result.state == "up"

    def test_pass_when_state_is_down(self) -> None:
        """Passes when interface is down and expected_state is 'down'."""
        dut = _make_mock_dut()
        dut.get_wan_interface_status.return_value = {
            "wan1": _make_link_status("wan1", "down"),
        }
        uc.assert_wan_interface_status(dut, "wan1", "down")

    def test_pass_when_state_is_degraded(self) -> None:
        """Passes when interface is degraded and expected_state is 'degraded'."""
        dut = _make_mock_dut()
        dut.get_wan_interface_status.return_value = {
            "wan1": _make_link_status("wan1", "degraded"),
        }
        uc.assert_wan_interface_status(dut, "wan1", "degraded")

    def test_fail_when_state_mismatches(self) -> None:
        """AssertionError raised when interface state differs from expected_state."""
        dut = _make_mock_dut()
        dut.get_wan_interface_status.return_value = {
            "wan1": _make_link_status("wan1", "down"),
        }
        with pytest.raises(AssertionError, match="expected state 'up'"):
            uc.assert_wan_interface_status(dut, "wan1", "up")

    def test_fail_when_label_not_in_status(self) -> None:
        """AssertionError raised when wan_label is absent from the status dict."""
        dut = _make_mock_dut()
        dut.get_wan_interface_status.return_value = {
            "wan1": _make_link_status("wan1", "up"),
        }
        with pytest.raises(AssertionError, match="not found in DUT interface status"):
            uc.assert_wan_interface_status(dut, "wan2", "up")

    def test_assertion_includes_label(self) -> None:
        """Scenario label is included in assertion messages on failure."""
        dut = _make_mock_dut()
        dut.get_wan_interface_status.return_value = {
            "wan1": _make_link_status("wan1", "down"),
        }
        with pytest.raises(AssertionError, match=r"\[link-check\]"):
            uc.assert_wan_interface_status(dut, "wan1", "up", label="link-check")

    def test_multiple_links_selects_correct_one(self) -> None:
        """Selects and returns only the requested WAN link from a multi-link status dict."""
        dut = _make_mock_dut()
        dut.get_wan_interface_status.return_value = {
            "wan1": _make_link_status("wan1", "up", "10.0.1.1"),
            "wan2": _make_link_status("wan2", "down", "10.0.2.1"),
        }
        status = uc.assert_wan_interface_status(dut, "wan2", "down")
        assert status.ip_address == "10.0.2.1"


# ---------------------------------------------------------------------------
# assert_path_metrics_within_slo()
# ---------------------------------------------------------------------------


class TestAssertPathMetricsWithinSlo:
    """Tests for assert_path_metrics_within_slo()."""

    def test_all_metrics_pass(self) -> None:
        """Returns PathMetrics when latency, jitter, and loss are all within SLO."""
        dut = _make_mock_dut()
        dut.get_wan_path_metrics.return_value = {
            "wan1": _make_path_metrics(latency_ms=10.0, jitter_ms=2.0, loss_percent=0.1),
        }
        m = uc.assert_path_metrics_within_slo(
            dut, "wan1", max_latency_ms=50.0, max_jitter_ms=10.0, max_loss_percent=1.0
        )
        assert isinstance(m, PathMetrics)

    def test_only_latency_checked(self) -> None:
        """Passes when only max_latency_ms is provided and it is not exceeded."""
        dut = _make_mock_dut()
        dut.get_wan_path_metrics.return_value = {
            "wan1": _make_path_metrics(latency_ms=30.0, jitter_ms=100.0, loss_percent=50.0),
        }
        uc.assert_path_metrics_within_slo(dut, "wan1", max_latency_ms=50.0)

    def test_latency_exceeded_raises(self) -> None:
        """AssertionError raised when latency exceeds max_latency_ms."""
        dut = _make_mock_dut()
        dut.get_wan_path_metrics.return_value = {
            "wan1": _make_path_metrics(latency_ms=60.0),
        }
        with pytest.raises(AssertionError, match="latency.*exceeds SLO"):
            uc.assert_path_metrics_within_slo(dut, "wan1", max_latency_ms=50.0)

    def test_jitter_exceeded_raises(self) -> None:
        """AssertionError raised when jitter exceeds max_jitter_ms."""
        dut = _make_mock_dut()
        dut.get_wan_path_metrics.return_value = {
            "wan1": _make_path_metrics(jitter_ms=15.0),
        }
        with pytest.raises(AssertionError, match="jitter.*exceeds SLO"):
            uc.assert_path_metrics_within_slo(dut, "wan1", max_jitter_ms=10.0)

    def test_loss_exceeded_raises(self) -> None:
        """AssertionError raised when loss_percent exceeds max_loss_percent."""
        dut = _make_mock_dut()
        dut.get_wan_path_metrics.return_value = {
            "wan1": _make_path_metrics(loss_percent=2.5),
        }
        with pytest.raises(AssertionError, match="packet loss.*exceeds SLO"):
            uc.assert_path_metrics_within_slo(dut, "wan1", max_loss_percent=1.0)

    def test_missing_wan_label_raises(self) -> None:
        """AssertionError raised when wan_label is not in the metrics dict."""
        dut = _make_mock_dut()
        dut.get_wan_path_metrics.return_value = {
            "wan1": _make_path_metrics(),
        }
        with pytest.raises(AssertionError, match="not found in path metrics"):
            uc.assert_path_metrics_within_slo(dut, "wan2", max_latency_ms=50.0)

    def test_at_exactly_slo_boundary_passes(self) -> None:
        """Passes when all metrics are exactly equal to their SLO thresholds."""
        dut = _make_mock_dut()
        dut.get_wan_path_metrics.return_value = {
            "wan1": _make_path_metrics(latency_ms=50.0, jitter_ms=10.0, loss_percent=1.0),
        }
        uc.assert_path_metrics_within_slo(
            dut, "wan1", max_latency_ms=50.0, max_jitter_ms=10.0, max_loss_percent=1.0
        )

    def test_assertion_includes_label(self) -> None:
        """Scenario label appears in assertion message on failure."""
        dut = _make_mock_dut()
        dut.get_wan_path_metrics.return_value = {
            "wan1": _make_path_metrics(latency_ms=100.0),
        }
        with pytest.raises(AssertionError, match=r"\[slo-check\]"):
            uc.assert_path_metrics_within_slo(
                dut, "wan1", max_latency_ms=50.0, label="slo-check"
            )

    def test_no_thresholds_returns_metrics_without_raising(self) -> None:
        """No exception raised and full PathMetrics returned when all thresholds are None.

        When no threshold is specified, the function skips all checks.  The
        return value must still be the correct PathMetrics for the requested
        WAN label — confirming the function looked up and returned the right
        entry even when no assertions were made.
        """
        dut = _make_mock_dut()
        dut.get_wan_path_metrics.return_value = {
            "wan1": _make_path_metrics(latency_ms=999.0, jitter_ms=999.0, loss_percent=99.9),
        }
        m = uc.assert_path_metrics_within_slo(dut, "wan1")
        assert isinstance(m, PathMetrics)
        assert m.latency_ms == 999.0, (
            f"Expected latency_ms=999.0 from the mock, got {m.latency_ms}"
        )


# ---------------------------------------------------------------------------
# measure_failover_convergence()
# ---------------------------------------------------------------------------


class TestMeasureFailoverConvergence:
    """Tests for measure_failover_convergence()."""

    @patch("boardfarm3.use_cases.wan_edge.tc_use_cases.inject_blackout")
    def test_returns_convergence_time_in_ms(self, mock_inject: MagicMock) -> None:
        """Returns a positive float (ms) when DUT switches to backup_link."""
        dut = _make_mock_dut()
        tc = _make_mock_tc()
        dut.get_active_wan_interface.side_effect = ["wan1", "wan2"]
        result = uc.measure_failover_convergence(
            dut, tc, primary_link="wan1", backup_link="wan2",
            poll_interval_ms=0, timeout_ms=2_000,
        )
        assert isinstance(result, float)
        assert result >= 0

    @patch("boardfarm3.use_cases.wan_edge.tc_use_cases.inject_blackout")
    def test_inject_blackout_called_with_extended_duration(self, mock_inject: MagicMock) -> None:
        """inject_blackout is called with timeout_ms + 1000 ms to outlast the convergence window."""
        dut = _make_mock_dut()
        tc = _make_mock_tc()
        dut.get_active_wan_interface.return_value = "wan2"
        uc.measure_failover_convergence(
            dut, tc, primary_link="wan1", backup_link="wan2",
            poll_interval_ms=0, timeout_ms=1_000,
        )
        mock_inject.assert_called_once_with(tc, duration_ms=2_000)

    @patch("boardfarm3.use_cases.wan_edge.tc_use_cases.inject_blackout")
    def test_raises_when_dut_does_not_converge(self, mock_inject: MagicMock) -> None:
        """AssertionError raised when DUT never switches within timeout_ms."""
        dut = _make_mock_dut()
        tc = _make_mock_tc()
        dut.get_active_wan_interface.return_value = "wan1"
        with pytest.raises(AssertionError, match="did not switch"):
            uc.measure_failover_convergence(
                dut, tc, primary_link="wan1", backup_link="wan2",
                poll_interval_ms=0, timeout_ms=0,
            )

    @patch("boardfarm3.use_cases.wan_edge.tc_use_cases.inject_blackout")
    def test_convergence_time_increases_with_polls(self, mock_inject: MagicMock) -> None:
        """Convergence time is larger the more polls are needed before switch occurs."""
        dut_fast = _make_mock_dut()
        tc_fast = _make_mock_tc()
        dut_fast.get_active_wan_interface.return_value = "wan2"
        t_fast = uc.measure_failover_convergence(
            dut_fast, tc_fast, primary_link="wan1", backup_link="wan2",
            poll_interval_ms=0, timeout_ms=2_000,
        )

        dut_slow = _make_mock_dut()
        tc_slow = _make_mock_tc()
        # 5 polls still on wan1, then switches
        dut_slow.get_active_wan_interface.side_effect = ["wan1"] * 5 + ["wan2"]
        t_slow = uc.measure_failover_convergence(
            dut_slow, tc_slow, primary_link="wan1", backup_link="wan2",
            poll_interval_ms=0, timeout_ms=2_000,
        )
        # Slow convergence must be >= fast convergence (both ≥ 0)
        assert t_slow >= t_fast


# ---------------------------------------------------------------------------
# assert_failover_time()
# ---------------------------------------------------------------------------


class TestAssertFailoverTime:
    """Tests for assert_failover_time()."""

    @patch("boardfarm3.use_cases.wan_edge.tc_use_cases.inject_blackout")
    def test_pass_when_convergence_within_slo(self, mock_inject: MagicMock) -> None:
        """Returns convergence time when it is at or below max_ms."""
        dut = _make_mock_dut()
        tc = _make_mock_tc()
        dut.get_active_wan_interface.return_value = "wan2"
        result = uc.assert_failover_time(
            dut, tc, primary_link="wan1", backup_link="wan2",
            max_ms=3_000,
        )
        assert isinstance(result, float)
        assert result <= 3_000

    @patch("boardfarm3.use_cases.wan_edge.measure_failover_convergence")
    def test_fail_when_convergence_exceeds_slo(self, mock_measure: MagicMock) -> None:
        """SLO assertion in assert_failover_time raises when measured convergence > max_ms.

        Patches measure_failover_convergence to return a fixed value (5 000 ms)
        so the SLO check inside assert_failover_time is actually reached — the
        previous implementation let measure_failover_convergence time out first,
        meaning the SLO assertion was never executed.
        """
        mock_measure.return_value = 5_000.0
        dut = _make_mock_dut()
        tc = _make_mock_tc()
        with pytest.raises(AssertionError, match="exceeded SLO"):
            uc.assert_failover_time(
                dut, tc, primary_link="wan1", backup_link="wan2",
                max_ms=1.0,
            )

    @patch("boardfarm3.use_cases.wan_edge.measure_failover_convergence")
    def test_assertion_message_includes_label(self, mock_measure: MagicMock) -> None:
        """Label appears in the SLO assertion message when convergence exceeds max_ms.

        Patches measure_failover_convergence to return a value that exceeds
        max_ms, forcing the SLO assertion to fire.  The match= pattern then
        confirms the label is embedded in the failure message.
        """
        mock_measure.return_value = 5_000.0
        dut = _make_mock_dut()
        tc = _make_mock_tc()
        with pytest.raises(AssertionError, match=r"\[convergence-slo\]"):
            uc.assert_failover_time(
                dut, tc, primary_link="wan1", backup_link="wan2",
                max_ms=1.0, label="convergence-slo",
            )
