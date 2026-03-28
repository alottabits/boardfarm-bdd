"""Unit tests for SD-WAN step definitions.

Each step is tested for both assessment outcomes:
- Statement is true  → step passes (correct acceptance)
- Statement is not true → step fails / raises (correct rejection)

Mocks: MockWANEdgeDevice, MockTrafficController, MockQoEClient, MockContext.
Patches: use_case modules at the step's import site (tests.step_defs.sdwan_steps.*).
"""

from __future__ import annotations

import inspect
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from tests.unit.mocks import (
    MockContext,
    MockQoEClient,
    MockTrafficController,
    MockTrafficGenerator,
    MockWANEdgeDevice,
)
from tests.step_defs.sdwan_steps import (
    APP_CONFIG,
    _get_app_config,
    _get_tc_for_wan,
    appliance_converges_within_slo,
    appliance_fails_back,
    appliance_steers_traffic,
    network_conditions_set_to_preset,
    network_ops_starts_upstream_traffic,
    network_ops_stops_upstream_traffic,
    network_ops_verifies_active_path,
    network_ops_verifies_active_path_given,
    network_ops_verifies_wan_links_up,
    remote_worker_confirms_responsive,
    remote_worker_confirms_session_functional,
    remote_worker_starts_session,
    sdwan_appliance_operational,
    traffic_generators_available,
    wan_link_complete_failure,
    wan_link_degraded,
    wan_link_recovers,
)


def _run_step(step_fn, *args, **kwargs):
    """Execute the setup portion of a step function.

    Yielding steps (generator functions) are advanced to the first yield so
    the setup code runs.  Non-yielding steps are called normally.  The
    generator (or None) is returned so tests can optionally verify teardown.
    """
    result = step_fn(*args, **kwargs)
    if inspect.isgenerator(result):
        next(result)
        return result
    return result


def _make_wan_edge_mock(**overrides) -> MagicMock:
    """Create a MagicMock for wan_edge_use_cases with unsafe=True.

    MagicMock rejects attribute names starting with 'assert_' unless
    unsafe=True is set.  Use-case functions like assert_active_path and
    assert_wan_interface_status hit this restriction.
    """
    return MagicMock(unsafe=True, **overrides)


def _make_qoe_mock(**overrides) -> MagicMock:
    """Create a MagicMock for qoe_use_cases with unsafe=True."""
    return MagicMock(unsafe=True, **overrides)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def bf_context():
    """Pre-populated context with mock SDWAN devices."""
    ctx = MockContext()
    ctx.sdwan_appliance = MockWANEdgeDevice()
    ctx.wan1_tc = MockTrafficController("wan1_tc")
    ctx.wan2_tc = MockTrafficController("wan2_tc")
    ctx.lan_client = MockQoEClient("lan_qoe_client")
    return ctx


@pytest.fixture
def mock_boardfarm_config():
    """Minimal boardfarm config with impairment presets."""
    return SimpleNamespace(
        env_config={
            "environment_def": {
                "impairment_presets": {
                    "pristine": {
                        "latency_ms": 5,
                        "jitter_ms": 1,
                        "loss_percent": 0,
                        "bandwidth_limit_mbps": 1000,
                    },
                    "4g_mobile": {
                        "latency_ms": 80,
                        "jitter_ms": 30,
                        "loss_percent": 1,
                        "bandwidth_limit_mbps": 20,
                    },
                }
            }
        }
    )


# ===========================================================================
# Test: sdwan_appliance_operational
# ===========================================================================


class TestSdwanApplianceOperational:
    """Tests for 'the SD-WAN appliance is operational …'."""

    def test_success_all_devices_discovered(self):
        """Statement is true: all devices discoverable → context populated."""
        ctx = MockContext()
        mock_tc1 = MockTrafficController("wan1_tc")
        mock_tc2 = MockTrafficController("wan2_tc")
        mock_qoe_client = MockQoEClient()
        with (
            patch(
                "tests.step_defs.sdwan_steps.wan_edge_use_cases"
            ) as mock_we,
            patch(
                "tests.step_defs.sdwan_steps.tc_use_cases"
            ) as mock_tc,
            patch(
                "tests.step_defs.sdwan_steps.qoe_use_cases"
            ) as mock_qoe,
        ):
            mock_edge = MockWANEdgeDevice()
            mock_we.get_wan_edge.return_value = mock_edge
            mock_tc.get_traffic_controller.side_effect = [
                mock_tc1,
                mock_tc2,
            ]
            mock_qoe.get_qoe_client.return_value = (
                mock_qoe_client
            )

            sdwan_appliance_operational(ctx)

            mock_we.get_wan_edge.assert_called_once()
            assert (
                mock_tc.get_traffic_controller.call_count == 2
            )
            mock_qoe.get_qoe_client.assert_called_once()
            assert ctx.sdwan_appliance is mock_edge
            assert ctx.wan1_tc is mock_tc1
            assert ctx.wan2_tc is mock_tc2
            assert ctx.lan_client is mock_qoe_client

    def test_failure_no_wan_edge_device(self):
        """Statement is not true: no WANEdgeDevice → step raises."""
        ctx = MockContext()
        with (
            patch(
                "tests.step_defs.sdwan_steps.wan_edge_use_cases"
            ) as mock_we,
            patch("tests.step_defs.sdwan_steps.tc_use_cases"),
            patch("tests.step_defs.sdwan_steps.qoe_use_cases"),
        ):
            mock_we.get_wan_edge.side_effect = Exception(
                "No WANEdgeDevice available"
            )
            with pytest.raises(
                Exception, match="No WANEdgeDevice"
            ):
                sdwan_appliance_operational(ctx)


# ===========================================================================
# Test: network_conditions_set_to_preset
# ===========================================================================


class TestNetworkConditionsPreset:
    """Tests for 'the network conditions are set to "<preset>" …'."""

    def test_success_preset_applied(
        self, bf_context, mock_boardfarm_config
    ):
        """Statement is true: preset applied to both TCs."""
        with patch(
            "tests.step_defs.sdwan_steps.tc_use_cases"
        ) as mock_tc:
            _run_step(
                network_conditions_set_to_preset,
                bf_context, "pristine", mock_boardfarm_config,
            )
            assert mock_tc.apply_preset.call_count == 2
            mock_tc.apply_preset.assert_any_call(
                bf_context.wan1_tc,
                "pristine",
                mock_boardfarm_config,
            )
            mock_tc.apply_preset.assert_any_call(
                bf_context.wan2_tc,
                "pristine",
                mock_boardfarm_config,
            )

    def test_failure_unknown_preset(
        self, bf_context, mock_boardfarm_config
    ):
        """Statement is not true: unknown preset → step raises."""
        with patch(
            "tests.step_defs.sdwan_steps.tc_use_cases"
        ) as mock_tc:
            mock_tc.apply_preset.side_effect = KeyError(
                "Preset 'bogus' not found"
            )
            with pytest.raises(KeyError, match="bogus"):
                _run_step(
                    network_conditions_set_to_preset,
                    bf_context, "bogus", mock_boardfarm_config,
                )


# ===========================================================================
# Test: network_ops_verifies_wan_links_up
# ===========================================================================


class TestNetworkOpsVerifiesWanLinksUp:
    """Tests for 'network operations verifies that both WAN links are in UP state'."""

    def test_success_both_up(self, bf_context):
        """Statement is true: both links UP → step passes."""
        mock_we = _make_wan_edge_mock()
        with patch(
            "tests.step_defs.sdwan_steps.wan_edge_use_cases",
            mock_we,
        ):
            network_ops_verifies_wan_links_up(bf_context)

            assert (
                mock_we.assert_wan_interface_status.call_count
                == 2
            )
            mock_we.assert_wan_interface_status.assert_any_call(
                bf_context.sdwan_appliance, "wan1", "up"
            )
            mock_we.assert_wan_interface_status.assert_any_call(
                bf_context.sdwan_appliance, "wan2", "up"
            )

    def test_failure_wan1_down(self, bf_context):
        """Statement is not true: wan1 is down → step raises."""
        mock_we = _make_wan_edge_mock()
        mock_we.assert_wan_interface_status.side_effect = [
            AssertionError("wan1 state 'down' != 'up'"),
        ]
        with patch(
            "tests.step_defs.sdwan_steps.wan_edge_use_cases",
            mock_we,
        ):
            with pytest.raises(AssertionError, match="wan1"):
                network_ops_verifies_wan_links_up(bf_context)


# ===========================================================================
# Test: network_ops_verifies_active_path
# ===========================================================================


class TestNetworkOpsVerifiesActivePathGiven:
    """Tests for the Given variant (polls via wait_for_path_switch)."""

    def test_success_wan1_active(self, bf_context):
        """wan1 converges within timeout → step passes."""
        mock_we = _make_wan_edge_mock()
        mock_we.wait_for_path_switch.return_value = 250.0
        with patch(
            "tests.step_defs.sdwan_steps.wan_edge_use_cases",
            mock_we,
        ):
            network_ops_verifies_active_path_given(
                bf_context, "wan1"
            )

            mock_we.wait_for_path_switch.assert_called_once_with(
                bf_context.sdwan_appliance,
                "wan1",
                timeout_ms=10_000,
            )

    def test_failure_timeout(self, bf_context):
        """wan1 does not converge → step raises."""
        mock_we = _make_wan_edge_mock()
        mock_we.wait_for_path_switch.side_effect = (
            AssertionError(
                "Device did not switch to 'wan1' within 10000ms"
            )
        )
        with patch(
            "tests.step_defs.sdwan_steps.wan_edge_use_cases",
            mock_we,
        ):
            with pytest.raises(
                AssertionError, match="wan1.*10000"
            ):
                network_ops_verifies_active_path_given(
                    bf_context, "wan1"
                )


class TestNetworkOpsVerifiesActivePath:
    """Tests for the Then variant (instant assert_active_path)."""

    def test_success_wan1_active(self, bf_context):
        """Statement is true: wan1 is active → step passes."""
        mock_we = _make_wan_edge_mock()
        with patch(
            "tests.step_defs.sdwan_steps.wan_edge_use_cases",
            mock_we,
        ):
            network_ops_verifies_active_path(
                bf_context, "wan1"
            )

            mock_we.assert_active_path.assert_called_once_with(
                bf_context.sdwan_appliance, "wan1"
            )

    def test_failure_wrong_path(self, bf_context):
        """Statement is not true: wrong path → step raises."""
        mock_we = _make_wan_edge_mock()
        mock_we.assert_active_path.side_effect = (
            AssertionError(
                "Expected 'wan1' but Device reports 'wan2'"
            )
        )
        with patch(
            "tests.step_defs.sdwan_steps.wan_edge_use_cases",
            mock_we,
        ):
            with pytest.raises(
                AssertionError, match="wan1.*wan2"
            ):
                network_ops_verifies_active_path(
                    bf_context, "wan1"
                )


# ===========================================================================
# Test: _get_app_config helper
# ===========================================================================


class TestGetAppConfig:
    """Tests for the _get_app_config dispatch helper."""

    @pytest.mark.parametrize(
        "app_type", ["productivity", "streaming", "conferencing"]
    )
    def test_known_app_type_returns_config(self, app_type):
        """Known app_type returns correct entry from APP_CONFIG."""
        cfg = _get_app_config(app_type)
        assert cfg is APP_CONFIG[app_type]
        assert "measure" in cfg
        assert "assert_slo" in cfg
        assert "url" in cfg
        assert "slo_kwargs" in cfg

    def test_unknown_app_type_raises(self):
        """Unknown app_type raises ValueError."""
        with pytest.raises(ValueError, match="unknown_app"):
            _get_app_config("unknown_app")


# ===========================================================================
# Test: remote_worker_starts_session (parameterized by app_type)
# ===========================================================================


class TestRemoteWorkerStartsSession:
    """Tests for 'the remote worker starts a "<app_type>" session …'."""

    @pytest.mark.parametrize(
        "app_type,measure_fn,expected_url,"
        "expected_measure_kwargs",
        [
            (
                "productivity",
                "measure_productivity",
                "http://172.16.0.10:8080/",
                {},
            ),
            (
                "streaming",
                "measure_streaming",
                "http://172.16.0.11:8081/hls/default/index.m3u8",
                {"duration_s": 15},
            ),
            (
                "conferencing",
                "measure_conferencing",
                "wss://172.16.0.12:8443/room",
                {"duration_s": 10},
            ),
        ],
    )
    def test_success_session_started(
        self,
        bf_context,
        app_type,
        measure_fn,
        expected_url,
        expected_measure_kwargs,
    ):
        """Statement is true: measurement succeeds → baseline and config stored."""
        mock_result = SimpleNamespace(success=True)
        mock_qoe = _make_qoe_mock()
        getattr(mock_qoe, measure_fn).return_value = (
            mock_result
        )
        with patch(
            "tests.step_defs.sdwan_steps.qoe_use_cases",
            mock_qoe,
        ):
            remote_worker_starts_session(
                bf_context, app_type
            )

            getattr(
                mock_qoe, measure_fn
            ).assert_called_once_with(
                bf_context.lan_client,
                expected_url,
                **expected_measure_kwargs,
            )
            assert (
                bf_context.app_session_baseline is mock_result
            )
            assert bf_context.app_type == app_type
            assert (
                bf_context.app_config is APP_CONFIG[app_type]
            )

    @pytest.mark.parametrize(
        "app_type,measure_fn",
        [
            ("productivity", "measure_productivity"),
            ("streaming", "measure_streaming"),
            ("conferencing", "measure_conferencing"),
        ],
    )
    def test_failure_measurement_fails(
        self, bf_context, app_type, measure_fn
    ):
        """Statement is not true: measurement raises → step raises."""
        mock_qoe = _make_qoe_mock()
        getattr(mock_qoe, measure_fn).side_effect = (
            ConnectionError("Application unreachable")
        )
        with patch(
            "tests.step_defs.sdwan_steps.qoe_use_cases",
            mock_qoe,
        ):
            with pytest.raises(
                ConnectionError, match="unreachable"
            ):
                remote_worker_starts_session(
                    bf_context, app_type
                )


# ===========================================================================
# Test: remote_worker_confirms_responsive (parameterized by app_type)
# ===========================================================================


class TestRemoteWorkerConfirmsResponsive:
    """Tests for 'the remote worker confirms the "<app_type>" session is responsive'."""

    @pytest.mark.parametrize(
        "app_type,assert_slo_fn,expected_kwargs",
        [
            (
                "productivity",
                "assert_productivity_slo",
                {
                    "max_ttfb_ms": 200,
                    "max_load_time_ms": 15000,
                },
            ),
            (
                "streaming",
                "assert_streaming_slo",
                {
                    "max_startup_time_ms": 5000,
                    "max_rebuffer_ratio": 0.0,
                },
            ),
            (
                "conferencing",
                "assert_conferencing_slo",
                {"min_mos": 3.5},
            ),
        ],
    )
    def test_success_responsive(
        self,
        bf_context,
        app_type,
        assert_slo_fn,
        expected_kwargs,
    ):
        """Statement is true: baseline within SLO → step passes."""
        mock_result = SimpleNamespace(success=True)
        bf_context.app_session_baseline = mock_result
        mock_qoe = _make_qoe_mock()
        with patch(
            "tests.step_defs.sdwan_steps.qoe_use_cases",
            mock_qoe,
        ):
            remote_worker_confirms_responsive(
                bf_context, app_type
            )

            getattr(
                mock_qoe, assert_slo_fn
            ).assert_called_once_with(
                mock_result, **expected_kwargs
            )

    @pytest.mark.parametrize(
        "app_type,assert_slo_fn",
        [
            ("productivity", "assert_productivity_slo"),
            ("streaming", "assert_streaming_slo"),
            ("conferencing", "assert_conferencing_slo"),
        ],
    )
    def test_failure_slo_violated(
        self, bf_context, app_type, assert_slo_fn
    ):
        """Statement is not true: baseline exceeds SLO → step raises."""
        bf_context.app_session_baseline = SimpleNamespace(
            success=True
        )
        mock_qoe = _make_qoe_mock()
        getattr(mock_qoe, assert_slo_fn).side_effect = (
            AssertionError("SLO violation")
        )
        with patch(
            "tests.step_defs.sdwan_steps.qoe_use_cases",
            mock_qoe,
        ):
            with pytest.raises(
                AssertionError, match="SLO violation"
            ):
                remote_worker_confirms_responsive(
                    bf_context, app_type
                )


# ===========================================================================
# Test: remote_worker_confirms_session_functional (parameterized)
# ===========================================================================


class TestRemoteWorkerConfirmsSessionFunctional:
    """Tests for 'the remote worker confirms the "<app_type>" session remains functional …'."""

    @pytest.mark.parametrize(
        "app_type,measure_fn,assert_slo_fn,"
        "expected_url,expected_measure_kwargs,"
        "expected_slo_kwargs",
        [
            (
                "productivity",
                "measure_productivity",
                "assert_productivity_slo",
                "http://172.16.0.10:8080/",
                {},
                {
                    "max_ttfb_ms": 200,
                    "max_load_time_ms": 15000,
                },
            ),
            (
                "streaming",
                "measure_streaming",
                "assert_streaming_slo",
                "http://172.16.0.11:8081/hls/default/index.m3u8",
                {"duration_s": 15},
                {
                    "max_startup_time_ms": 5000,
                    "max_rebuffer_ratio": 0.0,
                },
            ),
            (
                "conferencing",
                "measure_conferencing",
                "assert_conferencing_slo",
                "wss://172.16.0.12:8443/room",
                {"duration_s": 10},
                {"min_mos": 3.5},
            ),
        ],
    )
    def test_success_session_functional(
        self,
        bf_context,
        app_type,
        measure_fn,
        assert_slo_fn,
        expected_url,
        expected_measure_kwargs,
        expected_slo_kwargs,
    ):
        """Statement is true: re-measurement within SLO → step passes."""
        mock_result = SimpleNamespace(success=True)
        mock_qoe = _make_qoe_mock()
        getattr(mock_qoe, measure_fn).return_value = (
            mock_result
        )
        with patch(
            "tests.step_defs.sdwan_steps.qoe_use_cases",
            mock_qoe,
        ):
            remote_worker_confirms_session_functional(
                bf_context, app_type
            )

            getattr(
                mock_qoe, measure_fn
            ).assert_called_once_with(
                bf_context.lan_client,
                expected_url,
                **expected_measure_kwargs,
            )
            getattr(
                mock_qoe, assert_slo_fn
            ).assert_called_once_with(
                mock_result, **expected_slo_kwargs
            )
            assert bf_context.last_qoe_result is mock_result

    @pytest.mark.parametrize(
        "app_type,measure_fn,assert_slo_fn",
        [
            (
                "productivity",
                "measure_productivity",
                "assert_productivity_slo",
            ),
            (
                "streaming",
                "measure_streaming",
                "assert_streaming_slo",
            ),
            (
                "conferencing",
                "measure_conferencing",
                "assert_conferencing_slo",
            ),
        ],
    )
    def test_failure_slo_violated(
        self,
        bf_context,
        app_type,
        measure_fn,
        assert_slo_fn,
    ):
        """Statement is not true: SLO violated → step raises."""
        mock_result = SimpleNamespace(success=True)
        mock_qoe = _make_qoe_mock()
        getattr(mock_qoe, measure_fn).return_value = (
            mock_result
        )
        getattr(mock_qoe, assert_slo_fn).side_effect = (
            AssertionError("SLO violation")
        )
        with patch(
            "tests.step_defs.sdwan_steps.qoe_use_cases",
            mock_qoe,
        ):
            with pytest.raises(
                AssertionError, match="SLO violation"
            ):
                remote_worker_confirms_session_functional(
                    bf_context, app_type
                )

    @pytest.mark.parametrize(
        "app_type,measure_fn",
        [
            ("productivity", "measure_productivity"),
            ("streaming", "measure_streaming"),
            ("conferencing", "measure_conferencing"),
        ],
    )
    def test_failure_measurement_fails(
        self, bf_context, app_type, measure_fn
    ):
        """Statement is not true: measurement raises → step raises."""
        mock_qoe = _make_qoe_mock()
        getattr(mock_qoe, measure_fn).side_effect = (
            ConnectionError("Connection refused")
        )
        with patch(
            "tests.step_defs.sdwan_steps.qoe_use_cases",
            mock_qoe,
        ):
            with pytest.raises(
                ConnectionError, match="Connection refused"
            ):
                remote_worker_confirms_session_functional(
                    bf_context, app_type
                )


# ===========================================================================
# Test: wan_link_complete_failure
# ===========================================================================


class TestWanLinkCompleteFailure:
    """Tests for '"<wan>" experiences a complete link failure'."""

    def test_success_impairment_applied(self, bf_context):
        """Statement is true: 100% loss applied → context updated."""
        with patch(
            "tests.step_defs.sdwan_steps.tc_use_cases"
        ) as mock_tc:
            _run_step(wan_link_complete_failure, bf_context, "wan1")

            mock_tc.set_impairment_profile.assert_called_once()
            args = (
                mock_tc.set_impairment_profile.call_args
            )
            assert args[0][0] is bf_context.wan1_tc
            profile = args[0][1]
            assert profile.loss_percent == 100.0, (
                "Expected 100% loss but got"
                f" {profile.loss_percent}%"
            )
            assert bf_context.impaired_wan == "wan1"
            assert hasattr(bf_context, "failure_start_time")

    def test_failure_unknown_wan_link(self, bf_context):
        """Statement is not true: unknown WAN link → ValueError."""
        with pytest.raises(ValueError, match="wan3"):
            _run_step(wan_link_complete_failure, bf_context, "wan3")


# ===========================================================================
# Test: wan_link_degraded
# ===========================================================================


class TestWanLinkDegraded:
    """Tests for '"<wan>" experiences degraded conditions …'."""

    def test_success_preset_applied(
        self, bf_context, mock_boardfarm_config
    ):
        """Statement is true: degradation preset applied."""
        with patch(
            "tests.step_defs.sdwan_steps.tc_use_cases"
        ) as mock_tc:
            _run_step(
                wan_link_degraded,
                bf_context,
                "wan1",
                "4g_mobile",
                mock_boardfarm_config,
            )
            mock_tc.apply_preset.assert_called_once_with(
                bf_context.wan1_tc,
                "4g_mobile",
                mock_boardfarm_config,
            )
            assert bf_context.impaired_wan == "wan1"

    def test_failure_preset_not_found(
        self, bf_context, mock_boardfarm_config
    ):
        """Statement is not true: preset missing → step raises."""
        with patch(
            "tests.step_defs.sdwan_steps.tc_use_cases"
        ) as mock_tc:
            mock_tc.apply_preset.side_effect = KeyError(
                "Preset 'unknown' not found"
            )
            with pytest.raises(KeyError, match="unknown"):
                _run_step(
                    wan_link_degraded,
                    bf_context,
                    "wan1",
                    "unknown",
                    mock_boardfarm_config,
                )


# ===========================================================================
# Test: wan_link_recovers
# ===========================================================================


class TestWanLinkRecovers:
    """Tests for '"<wan>" recovers and returns to healthy state'."""

    def test_success_impairment_cleared(self, bf_context):
        """Statement is true: impairment cleared → step passes."""
        with patch(
            "tests.step_defs.sdwan_steps.tc_use_cases"
        ) as mock_tc:
            wan_link_recovers(bf_context, "wan1")

            mock_tc.clear_impairment.assert_called_once_with(
                bf_context.wan1_tc
            )
            assert hasattr(bf_context, "recovery_start_time")

    def test_failure_clear_raises(self, bf_context):
        """Statement is not true: clear fails → step raises."""
        with patch(
            "tests.step_defs.sdwan_steps.tc_use_cases"
        ) as mock_tc:
            mock_tc.clear_impairment.side_effect = Exception(
                "SSH connection lost"
            )
            with pytest.raises(
                Exception, match="SSH connection lost"
            ):
                wan_link_recovers(bf_context, "wan1")


# ===========================================================================
# Teardown verification for yielding steps
# ===========================================================================


class TestYieldTeardownBehavior:
    """Verify that yielding impairment steps clear impairments on teardown."""

    def test_complete_failure_teardown_clears(self, bf_context):
        """wan_link_complete_failure teardown calls clear_impairment."""
        with patch(
            "tests.step_defs.sdwan_steps.tc_use_cases"
        ) as mock_tc:
            gen = _run_step(wan_link_complete_failure, bf_context, "wan1")
            mock_tc.clear_impairment.reset_mock()

            with pytest.raises(StopIteration):
                next(gen)

            mock_tc.clear_impairment.assert_called_once_with(
                bf_context.wan1_tc
            )

    def test_degraded_teardown_clears(
        self, bf_context, mock_boardfarm_config
    ):
        """wan_link_degraded teardown calls clear_impairment."""
        with patch(
            "tests.step_defs.sdwan_steps.tc_use_cases"
        ) as mock_tc:
            gen = _run_step(
                wan_link_degraded,
                bf_context, "wan1", "4g_mobile", mock_boardfarm_config,
            )
            mock_tc.clear_impairment.reset_mock()

            with pytest.raises(StopIteration):
                next(gen)

            mock_tc.clear_impairment.assert_called_once_with(
                bf_context.wan1_tc
            )

    def test_preset_teardown_clears_both(
        self, bf_context, mock_boardfarm_config
    ):
        """network_conditions_set_to_preset teardown clears both TCs."""
        with patch(
            "tests.step_defs.sdwan_steps.tc_use_cases"
        ) as mock_tc:
            gen = _run_step(
                network_conditions_set_to_preset,
                bf_context, "pristine", mock_boardfarm_config,
            )
            mock_tc.clear_impairment.reset_mock()

            with pytest.raises(StopIteration):
                next(gen)

            assert mock_tc.clear_impairment.call_count == 2
            mock_tc.clear_impairment.assert_any_call(
                bf_context.wan1_tc
            )
            mock_tc.clear_impairment.assert_any_call(
                bf_context.wan2_tc
            )

    def test_teardown_swallows_exception(self, bf_context):
        """Teardown logs but does not re-raise clear_impairment failures."""
        with patch(
            "tests.step_defs.sdwan_steps.tc_use_cases"
        ) as mock_tc:
            gen = _run_step(wan_link_complete_failure, bf_context, "wan1")
            mock_tc.clear_impairment.side_effect = Exception("SSH lost")

            with pytest.raises(StopIteration):
                next(gen)


class TestTrafficGeneratorYieldTeardown:
    """Verify that the upstream-traffic step stops the flow on teardown.

    Teardown uses the captured flow_id (closure), not bf_context, so it
    always attempts to stop the flow it started — idempotent via try/except.
    """

    @pytest.fixture
    def bf_ctx_with_tg(self):
        ctx = MockContext()
        ctx.lan_traffic_gen = MockTrafficGenerator("lan_traffic_gen")
        ctx.north_traffic_gen = MockTrafficGenerator("north_traffic_gen")
        return ctx

    def test_teardown_stops_flow(self, bf_ctx_with_tg):
        """Teardown always calls stop_traffic with the captured flow_id."""
        with patch(
            "tests.step_defs.sdwan_steps.tg_use_cases"
        ) as mock_uc:
            mock_uc.saturate_wan_link.return_value = "flow-99"

            gen = _run_step(
                network_ops_starts_upstream_traffic,
                bf_ctx_with_tg, 85,
            )
            mock_uc.stop_traffic.reset_mock()

            with pytest.raises(StopIteration):
                next(gen)

            mock_uc.stop_traffic.assert_called_once_with(
                bf_ctx_with_tg.lan_traffic_gen, "flow-99"
            )

    def test_teardown_is_idempotent_after_explicit_stop(
        self, bf_ctx_with_tg
    ):
        """If the explicit stop step already ran, teardown still fires but swallows the error."""
        with patch(
            "tests.step_defs.sdwan_steps.tg_use_cases"
        ) as mock_uc:
            mock_uc.saturate_wan_link.return_value = "flow-99"

            gen = _run_step(
                network_ops_starts_upstream_traffic,
                bf_ctx_with_tg, 85,
            )
            mock_uc.stop_traffic.side_effect = RuntimeError(
                "Flow flow-99 not found (already stopped)"
            )

            with pytest.raises(StopIteration):
                next(gen)

            mock_uc.stop_traffic.assert_called_once_with(
                bf_ctx_with_tg.lan_traffic_gen, "flow-99"
            )

    def test_teardown_swallows_exception(self, bf_ctx_with_tg):
        """Teardown logs but does not re-raise stop_traffic failures."""
        with patch(
            "tests.step_defs.sdwan_steps.tg_use_cases"
        ) as mock_uc:
            mock_uc.saturate_wan_link.return_value = "flow-99"

            gen = _run_step(
                network_ops_starts_upstream_traffic,
                bf_ctx_with_tg, 85,
            )
            mock_uc.stop_traffic.side_effect = Exception(
                "iPerf3 process died"
            )

            with pytest.raises(StopIteration):
                next(gen)


# ===========================================================================
# Test: appliance_converges_within_slo
# ===========================================================================


class TestApplianceConvergesWithinSlo:
    """Tests for 'the appliance detects the failure and converges …'."""

    def test_success_convergence_within_slo(self, bf_context):
        """Statement is true: path switches quickly → convergence_ms stored."""
        with patch(
            "tests.step_defs.sdwan_steps.wan_edge_use_cases"
        ) as mock_we:
            mock_we.wait_for_path_switch.return_value = 150.0

            appliance_converges_within_slo(
                bf_context, "wan2", 1000
            )

            mock_we.wait_for_path_switch.assert_called_once_with(
                bf_context.sdwan_appliance,
                "wan2",
                timeout_ms=1000,
            )
            assert bf_context.convergence_ms == 150.0

    def test_failure_convergence_timeout(self, bf_context):
        """Statement is not true: path does not switch → step raises."""
        with patch(
            "tests.step_defs.sdwan_steps.wan_edge_use_cases"
        ) as mock_we:
            mock_we.wait_for_path_switch.side_effect = (
                AssertionError(
                    "Device did not switch to 'wan2'"
                    " within 1000ms"
                )
            )
            with pytest.raises(
                AssertionError, match="did not switch"
            ):
                appliance_converges_within_slo(
                    bf_context, "wan2", 1000
                )


# ===========================================================================
# Test: appliance_steers_traffic
# ===========================================================================


class TestApplianceSteersTraffic:
    """Tests for 'the appliance steers traffic to "<wan>"'."""

    def test_success_traffic_steered(self, bf_context):
        """Statement is true: Device steers to expected WAN."""
        with patch(
            "tests.step_defs.sdwan_steps.wan_edge_use_cases"
        ) as mock_we:
            mock_we.wait_for_path_switch.return_value = 2500.0

            appliance_steers_traffic(bf_context, "wan2")

            mock_we.wait_for_path_switch.assert_called_once_with(
                bf_context.sdwan_appliance,
                "wan2",
                timeout_ms=10_000,
            )

    def test_failure_no_steering(self, bf_context):
        """Statement is not true: Device does not steer → step raises."""
        with patch(
            "tests.step_defs.sdwan_steps.wan_edge_use_cases"
        ) as mock_we:
            mock_we.wait_for_path_switch.side_effect = (
                AssertionError("Device did not switch")
            )
            with pytest.raises(
                AssertionError, match="did not switch"
            ):
                appliance_steers_traffic(bf_context, "wan2")


# ===========================================================================
# Test: appliance_fails_back
# ===========================================================================


class TestApplianceFailsBack:
    """Tests for 'the appliance fails back to "<wan>" …'."""

    def test_success_failback(self, bf_context):
        """Statement is true: Device fails back → failback_ms stored."""
        with patch(
            "tests.step_defs.sdwan_steps.wan_edge_use_cases"
        ) as mock_we:
            mock_we.wait_for_path_switch.return_value = 5000.0

            appliance_fails_back(bf_context, "wan1")

            mock_we.wait_for_path_switch.assert_called_once_with(
                bf_context.sdwan_appliance,
                "wan1",
                timeout_ms=30_000,
            )
            assert bf_context.failback_ms == 5000.0

    def test_failure_no_failback(self, bf_context):
        """Statement is not true: Device does not fail back → raises."""
        with patch(
            "tests.step_defs.sdwan_steps.wan_edge_use_cases"
        ) as mock_we:
            mock_we.wait_for_path_switch.side_effect = (
                AssertionError(
                    "Device did not switch to 'wan1'"
                    " within 30000ms"
                )
            )
            with pytest.raises(
                AssertionError, match="did not switch"
            ):
                appliance_fails_back(bf_context, "wan1")


# ===========================================================================
# Test: _get_tc_for_wan helper
# ===========================================================================


class TestGetTcForWan:
    """Tests for the _get_tc_for_wan helper."""

    def test_wan1_resolved(self, bf_context):
        assert (
            _get_tc_for_wan(bf_context, "wan1")
            is bf_context.wan1_tc
        )

    def test_wan2_resolved(self, bf_context):
        assert (
            _get_tc_for_wan(bf_context, "wan2")
            is bf_context.wan2_tc
        )

    def test_unknown_raises(self, bf_context):
        with pytest.raises(ValueError, match="wan3"):
            _get_tc_for_wan(bf_context, "wan3")


# ---------------------------------------------------------------------------
# Traffic generator discovery
# ---------------------------------------------------------------------------


class TestTrafficGeneratorsAvailable:
    """Tests for the 'traffic generators are available' step."""

    def test_success_discovers_both_generators(self, bf_context):
        """Statement true: both traffic generators found → stored in context."""
        lan_tg = MockTrafficGenerator("lan_traffic_gen")
        north_tg = MockTrafficGenerator("north_traffic_gen")

        with patch(
            "tests.step_defs.sdwan_steps.tg_use_cases"
        ) as mock_uc:
            mock_uc.get_traffic_generator.side_effect = (
                lambda name: {
                    "lan_traffic_gen": lan_tg,
                    "north_traffic_gen": north_tg,
                }[name]
            )

            traffic_generators_available(bf_context)

            assert bf_context.lan_traffic_gen is lan_tg
            assert bf_context.north_traffic_gen is north_tg
            assert mock_uc.get_traffic_generator.call_count == 2

    def test_failure_propagates_device_not_found(self, bf_context):
        """Statement not true: device missing → raises."""
        with patch(
            "tests.step_defs.sdwan_steps.tg_use_cases"
        ) as mock_uc:
            mock_uc.get_traffic_generator.side_effect = Exception(
                "No TrafficGenerator devices available"
            )

            with pytest.raises(
                Exception, match="No TrafficGenerator"
            ):
                traffic_generators_available(bf_context)


# ---------------------------------------------------------------------------
# Network operations starts upstream traffic
# ---------------------------------------------------------------------------


class TestNetworkOpsStartsUpstreamTraffic:
    """Tests for the 'starts N Mbps upstream traffic' step."""

    @pytest.fixture
    def bf_ctx_with_tg(self):
        ctx = MockContext()
        ctx.lan_traffic_gen = MockTrafficGenerator("lan_traffic_gen")
        ctx.north_traffic_gen = MockTrafficGenerator("north_traffic_gen")
        return ctx

    def test_success_starts_flow_and_stores_id(self, bf_ctx_with_tg):
        """Statement true: flow started → flow_id stored in context."""
        with patch(
            "tests.step_defs.sdwan_steps.tg_use_cases"
        ) as mock_uc:
            mock_uc.saturate_wan_link.return_value = "flow-42"

            _run_step(
                network_ops_starts_upstream_traffic,
                bf_ctx_with_tg, 85,
            )

            mock_uc.saturate_wan_link.assert_called_once_with(
                source=bf_ctx_with_tg.lan_traffic_gen,
                destination=bf_ctx_with_tg.north_traffic_gen,
                link_bandwidth_mbps=100.0,
                dscp=0,
                utilisation_pct=0.85,
                duration_s=120,
            )
            assert bf_ctx_with_tg.upstream_flow_id == "flow-42"

    def test_failure_propagates_exception(self, bf_ctx_with_tg):
        """Statement not true: iPerf3 fails → raises."""
        with patch(
            "tests.step_defs.sdwan_steps.tg_use_cases"
        ) as mock_uc:
            mock_uc.saturate_wan_link.side_effect = RuntimeError(
                "iPerf3 connection refused"
            )

            with pytest.raises(
                RuntimeError, match="iPerf3 connection refused"
            ):
                _run_step(
                    network_ops_starts_upstream_traffic,
                    bf_ctx_with_tg, 85,
                )


# ---------------------------------------------------------------------------
# Network operations stops upstream traffic
# ---------------------------------------------------------------------------


class TestNetworkOpsStopsUpstreamTraffic:
    """Tests for the 'stops the upstream background traffic' step."""

    @pytest.fixture
    def bf_ctx_with_flow(self):
        ctx = MockContext()
        ctx.lan_traffic_gen = MockTrafficGenerator("lan_traffic_gen")
        ctx.upstream_flow_id = "flow-42"
        return ctx

    def test_success_stops_flow_and_stores_result(
        self, bf_ctx_with_flow
    ):
        """Statement true: flow stopped → result stored in context."""
        mock_result = SimpleNamespace(
            sent_mbps=85.0,
            received_mbps=84.5,
            loss_percent=0.1,
            jitter_ms=0.5,
            dscp_marking=0,
        )
        with patch(
            "tests.step_defs.sdwan_steps.tg_use_cases"
        ) as mock_uc:
            mock_uc.stop_traffic.return_value = mock_result

            network_ops_stops_upstream_traffic(bf_ctx_with_flow)

            mock_uc.stop_traffic.assert_called_once_with(
                bf_ctx_with_flow.lan_traffic_gen,
                "flow-42",
            )
            assert (
                bf_ctx_with_flow.upstream_traffic_result is mock_result
            )
            assert (
                bf_ctx_with_flow.upstream_traffic_result.sent_mbps
                == 85.0
            )

    def test_failure_propagates_exception(self, bf_ctx_with_flow):
        """Statement not true: stop fails → raises."""
        with patch(
            "tests.step_defs.sdwan_steps.tg_use_cases"
        ) as mock_uc:
            mock_uc.stop_traffic.side_effect = RuntimeError(
                "Flow not found"
            )

            with pytest.raises(
                RuntimeError, match="Flow not found"
            ):
                network_ops_stops_upstream_traffic(
                    bf_ctx_with_flow
                )
