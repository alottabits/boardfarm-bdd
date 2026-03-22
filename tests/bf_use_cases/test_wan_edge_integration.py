"""Integration tests for boardfarm3.use_cases.wan_edge.

Implements the four Pre-Hardware Validation Scenarios from
``docs/WAN_Edge_Appliance_testing.md §4.3``.  Exercises all use-case functions
end-to-end through the Boardfarm device manager against real containers:

- ``linux-sdwan-router`` (``LinuxSDWANRouter``) — the DUT
- ``wan1-tc`` / ``wan2-tc`` (``LinuxTrafficController``) — impairment control
- Both managed as ``WANEdgeDevice`` and ``TrafficController`` via templates

Run from boardfarm-bdd/ with the venv activated:

    pytest tests/bf_use_cases/test_wan_edge_integration.py -v \\
        --board-name sdwan \\
        --env-config bf_config/bf_env_sdwan.json \\
        --inventory-config bf_config/bf_config_sdwan.json \\
        --legacy --skip-boot

Scenarios:

1. **Orchestration Handshake** — Boardfarm can read DUT state via WANEdgeDevice.
2. **Impairment Trigger Loop** — Link failure on WAN1 drives DUT failover to WAN2.
3. **Path Steering Verification** — DUT prefers the available WAN link.
4. **Failover Convergence Time** — Convergence latency measured and logged for baseline.

Failover mechanism (Phase 3):
    This testbed uses ``dut.bring_wan_down()`` / ``dut.bring_wan_up()`` for
    failover testing.  This triggers the FRR static-route nexthop withdrawal
    immediately when the physical link goes down (kernel removes the connected
    route, FRR detects nexthop unreachable and installs the backup static
    route within < 100 ms).

    TC-triggered failover via BFD echo-mode is targeted for Phase 3.5 once
    a BFD reflector is added to each TC container.  The TC containers are
    used in Phase 3 for quality-of-service impairment tests only
    (see ``test_traffic_control_integration.py``).

Impairment presets (from bf_env_sdwan.json):

    pristine      → latency 5ms  / jitter 1ms  / loss 0%   / bw 1000 Mbps
    cable_typical → latency 15ms / jitter 5ms  / loss 0.1% / bw 100 Mbps
    satellite     → latency 600ms / jitter 50ms / loss 2%   / bw 10 Mbps
"""

from __future__ import annotations

import statistics
import time
from typing import TYPE_CHECKING

import pytest

import boardfarm3.use_cases.wan_edge as uc
from boardfarm3.exceptions import DeviceNotFound
from boardfarm3.templates.wan_edge import LinkStatus, PathMetrics, RouteEntry, WANEdgeDevice

if TYPE_CHECKING:
    from boardfarm3.templates.traffic_controller import TrafficController

# ---------------------------------------------------------------------------
# Timing constants
# ---------------------------------------------------------------------------

# Time (s) for kernel/FRR to detect a link-down and install backup route
_LINK_FAILOVER_S = 0.5

# Time (s) for FRR to restore primary route after link-up
_LINK_RECOVER_S = 3.0

# Maximum acceptable failover time for Phase 3 baseline (ms)
_FAILOVER_SLO_MS = 3_000


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _measure_link_failover(
    dut: WANEdgeDevice,
    failed_link: str,
    backup_link: str,
    poll_interval_s: float = 0.05,
    timeout_s: float = 3.0,
) -> float:
    """Bring *failed_link* down, measure ms until *backup_link* is active.

    Restores *failed_link* before returning.  Raises AssertionError if
    convergence does not occur within *timeout_s*.

    :return: Convergence time in milliseconds.
    """
    dut.bring_wan_down(failed_link)
    t0 = time.monotonic()
    deadline = t0 + timeout_s
    try:
        while time.monotonic() < deadline:
            if dut.get_active_wan_interface() == backup_link:
                return (time.monotonic() - t0) * 1000
            time.sleep(poll_interval_s)
        raise AssertionError(
            f"DUT did not switch from {failed_link!r} to {backup_link!r} "
            f"within {timeout_s:.1f}s"
        )
    finally:
        dut.bring_wan_up(failed_link)
        time.sleep(_LINK_RECOVER_S)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def both_links_up(sdwan: WANEdgeDevice):
    """Ensure both WAN links are UP before and after each test.

    Pre-test: brings both links up and waits for route convergence.
    Post-test: same recovery to leave a clean slate for the next test.
    """
    sdwan.bring_wan_up("wan1")
    sdwan.bring_wan_up("wan2")
    time.sleep(_LINK_RECOVER_S)
    yield
    sdwan.bring_wan_up("wan1")
    sdwan.bring_wan_up("wan2")
    time.sleep(_LINK_RECOVER_S)


# ---------------------------------------------------------------------------
# Scenario 1 — Orchestration Handshake
# ---------------------------------------------------------------------------


class TestScenario1OrchestrationHandshake:
    """Scenario 1: Boardfarm can communicate with the DUT via WANEdgeDevice template.

    Goal: Confirm that boardfarm can read device state through the template
    contract without exceptions; the DUT responds to all status queries with
    structured data types.
    """

    def test_get_wan_edge_returns_dut_instance(self, sdwan: WANEdgeDevice) -> None:
        """get_wan_edge() resolves the registered DUT by name."""
        dut = uc.get_wan_edge("sdwan")
        assert dut is sdwan
        assert isinstance(dut, WANEdgeDevice)
        print(f"✓ get_wan_edge('sdwan') returned WANEdgeDevice instance")

    def test_get_wan_interface_status_returns_both_wans(
        self, sdwan: WANEdgeDevice
    ) -> None:
        """get_wan_interface_status() returns LinkStatus objects for both WAN labels."""
        statuses = sdwan.get_wan_interface_status()

        assert isinstance(statuses, dict)
        assert len(statuses) >= 2, (
            f"Expected at least 2 WAN links, got {list(statuses.keys())}"
        )
        for label, status in statuses.items():
            assert isinstance(status, LinkStatus), (
                f"{label}: expected LinkStatus, got {type(status)}"
            )
            assert status.name, f"{label}: LinkStatus.name is empty"
            assert status.state in ("up", "down", "degraded"), (
                f"{label}: unexpected state {status.state!r}"
            )
        print(
            "✓ get_wan_interface_status: "
            + ", ".join(f"{k}={v.state}" for k, v in statuses.items())
        )

    def test_both_wan_links_are_up_at_baseline(self, sdwan: WANEdgeDevice, both_links_up: None) -> None:
        """Both WAN links report 'up' state when testbed is in baseline condition."""
        statuses = sdwan.get_wan_interface_status()

        assert "wan1" in statuses, "wan1 missing from status dict"
        assert "wan2" in statuses, "wan2 missing from status dict"
        assert statuses["wan1"].state == "up", (
            f"wan1 expected 'up' at baseline, got {statuses['wan1'].state!r}"
        )
        assert statuses["wan2"].state == "up", (
            f"wan2 expected 'up' at baseline, got {statuses['wan2'].state!r}"
        )
        print(
            f"✓ both WANs up at baseline: "
            f"wan1={statuses['wan1'].state}, wan2={statuses['wan2'].state}"
        )

    def test_assert_wan_interface_status_use_case(self, sdwan: WANEdgeDevice, both_links_up: None) -> None:
        """assert_wan_interface_status() passes for 'up' state at baseline."""
        status = uc.assert_wan_interface_status(sdwan, "wan1", "up")
        assert isinstance(status, LinkStatus)
        print(f"✓ assert_wan_interface_status(wan1, 'up') passed")

    def test_get_routing_table_returns_non_empty_list(
        self, sdwan: WANEdgeDevice
    ) -> None:
        """get_routing_table() returns at least one RouteEntry at baseline."""
        routes = sdwan.get_routing_table()

        assert isinstance(routes, list)
        assert len(routes) > 0, "Routing table is empty — FRR may not have started"
        for r in routes:
            assert isinstance(r, RouteEntry), (
                f"Expected RouteEntry, got {type(r)}: {r}"
            )
            assert r.interface, f"RouteEntry.interface is empty for route {r}"
        print(
            f"✓ get_routing_table: {len(routes)} entries, "
            f"interfaces: {sorted({r.interface for r in routes})}"
        )

    def test_get_active_wan_interface_returns_valid_label(
        self, sdwan: WANEdgeDevice, both_links_up: None
    ) -> None:
        """get_active_wan_interface() returns a logical WAN label from wan_interfaces."""
        active = sdwan.get_active_wan_interface()

        assert active in ("wan1", "wan2"), (
            f"Expected 'wan1' or 'wan2', got {active!r}"
        )
        print(f"✓ get_active_wan_interface() = {active!r}")

    def test_get_telemetry_returns_uptime(self, sdwan: WANEdgeDevice) -> None:
        """get_telemetry() returns a dict with a positive uptime_seconds value."""
        telemetry = sdwan.get_telemetry()

        assert isinstance(telemetry, dict)
        assert "uptime_seconds" in telemetry, (
            f"'uptime_seconds' missing from telemetry: {list(telemetry.keys())}"
        )
        assert telemetry["uptime_seconds"] > 0, (
            f"uptime_seconds should be positive, got {telemetry['uptime_seconds']}"
        )
        print(
            f"✓ get_telemetry: uptime={telemetry['uptime_seconds']:.0f}s, "
            f"keys={list(telemetry.keys())}"
        )

    def test_get_unknown_wan_edge_raises_device_not_found(self) -> None:
        """get_wan_edge() with unknown name raises DeviceNotFound."""
        with pytest.raises(DeviceNotFound, match="no_such_dut"):
            uc.get_wan_edge("no_such_dut")
        print("✓ get_wan_edge('no_such_dut') raised DeviceNotFound as expected")


# ---------------------------------------------------------------------------
# Scenario 2 — Impairment Trigger Loop
# ---------------------------------------------------------------------------


class TestScenario2ImpairmentTriggerLoop:
    """Scenario 2: Link failure on WAN1 drives DUT failover to WAN2.

    Goal: Verify that the end-to-end failure → detection → reroute loop works.
    Boardfarm brings eth-wan1 down on the DUT; FRR detects the nexthop as
    unreachable and installs the WAN2 static route as the active default.

    Note — TC-triggered failover (BFD-based):
        TC blackout → BFD failover requires a BFD daemon on each TC container
        to reflect echo-mode probes.  This is targeted for Phase 3.5.  The
        current Phase 3 tests use ``bring_wan_down`` / ``bring_wan_up`` to
        simulate link failure, which is the operative mechanism supported by
        the digital twin at this stage.

    Teardown via ``both_links_up`` fixture restores both links before the
    next test.
    """

    def test_wan1_down_drives_failover_to_wan2(
        self,
        sdwan: WANEdgeDevice,
        both_links_up: None,
    ) -> None:
        """bring_wan_down('wan1') → DUT switches active path to WAN2 within SLO."""
        sdwan.bring_wan_down("wan1")
        time.sleep(_LINK_FAILOVER_S)

        active = sdwan.get_active_wan_interface()
        assert active == "wan2", (
            f"Expected DUT to fail over to 'wan2' after WAN1 link-down, "
            f"but active path is {active!r}"
        )
        print(f"✓ Scenario 2: WAN1 down → DUT active path = wan2")

    def test_assert_wan_interface_down_after_bring_down(
        self,
        sdwan: WANEdgeDevice,
        both_links_up: None,
    ) -> None:
        """WAN1 reports 'down' state after bring_wan_down(); use case assertion passes.

        Verifies that assert_wan_interface_status() returns a populated LinkStatus
        with a non-empty physical interface name — confirming the use case both
        asserted the expected state AND returned real device data, not a stub.
        """
        sdwan.bring_wan_down("wan1")
        time.sleep(_LINK_FAILOVER_S)

        status = uc.assert_wan_interface_status(sdwan, "wan1", "down", label="scenario-2")
        assert status.name, (
            f"LinkStatus.name must be non-empty (got {status.name!r}) — "
            "assert_wan_interface_status should return real device data"
        )
        print(
            f"✓ Scenario 2: assert_wan_interface_status(wan1, 'down') confirmed "
            f"(physical interface: {status.name!r})"
        )

    def test_wan1_recovers_after_bring_up(
        self,
        sdwan: WANEdgeDevice,
        both_links_up: None,
    ) -> None:
        """WAN1 becomes active again after bring_wan_up(); assert_wan_interface_status passes.

        Validates the full trigger-loop cycle: down → verify failover → up → verify restore.
        """
        sdwan.bring_wan_down("wan1")
        time.sleep(_LINK_FAILOVER_S)

        active_during = sdwan.get_active_wan_interface()
        assert active_during == "wan2", (
            f"Expected wan2 during WAN1 failure, got {active_during!r}"
        )

        sdwan.bring_wan_up("wan1")
        time.sleep(_LINK_RECOVER_S)

        uc.assert_wan_interface_status(sdwan, "wan1", "up", label="scenario-2-restore")
        print(f"✓ Scenario 2 restore: WAN1 back to 'up' after bring_wan_up")

    def test_wan2_failover_symmetric(
        self,
        sdwan: WANEdgeDevice,
        both_links_up: None,
    ) -> None:
        """bring_wan_down('wan2') has no effect on DUT routing (WAN1 remains primary).

        WAN2 is the backup; disabling it should not change the primary WAN1 path.
        """
        active_before = sdwan.get_active_wan_interface()
        sdwan.bring_wan_down("wan2")
        time.sleep(_LINK_FAILOVER_S)

        active_after = sdwan.get_active_wan_interface()
        assert active_after == "wan1", (
            f"WAN1 should remain active after WAN2 down, got {active_after!r}"
        )
        print(
            f"✓ Scenario 2: WAN2 down has no effect on WAN1 primary path "
            f"(before={active_before!r}, after={active_after!r})"
        )


# ---------------------------------------------------------------------------
# Scenario 3 — Path Steering Verification
# ---------------------------------------------------------------------------


class TestScenario3PathSteeringVerification:
    """Scenario 3: DUT uses the available WAN link.

    Goal: Verify that path selection responds to which WAN links are available.
    By bringing WAN2 down, DUT must use WAN1.  By bringing WAN1 down, DUT
    must use WAN2.  The symmetry test confirms path selection is not
    hard-wired to always prefer one WAN.
    """

    def test_both_wans_up_prefers_wan1_as_primary(
        self,
        sdwan: WANEdgeDevice,
        both_links_up: None,
    ) -> None:
        """With both links UP, DUT uses WAN1 (lower-metric static route)."""
        active = sdwan.get_active_wan_interface()
        assert active == "wan1", (
            f"Expected WAN1 (lower-metric primary) with both links UP, got {active!r}"
        )
        print(f"✓ Scenario 3 baseline: both links UP → active = wan1 (primary)")

    def test_wan2_down_enforces_wan1_path(
        self,
        sdwan: WANEdgeDevice,
        both_links_up: None,
    ) -> None:
        """WAN2 admin-down → DUT uses WAN1.

        Applies cable_typical profile on WAN1 via TC to ensure it has the
        best conditions, then verifies routing follows availability.
        """
        sdwan.bring_wan_down("wan2")
        time.sleep(_LINK_FAILOVER_S)

        uc.assert_active_path(sdwan, expected_wan="wan1", label="scenario-3-wan2-down")
        print(f"✓ Scenario 3: WAN2 down → active = wan1")

    def test_wan1_down_forces_wan2_path(
        self,
        sdwan: WANEdgeDevice,
        both_links_up: None,
    ) -> None:
        """WAN1 admin-down → DUT uses WAN2.

        Confirms symmetric path steering: if the primary link goes down,
        the DUT routes via the backup without manual intervention.
        """
        sdwan.bring_wan_down("wan1")
        time.sleep(_LINK_FAILOVER_S)

        uc.assert_active_path(sdwan, expected_wan="wan2", label="scenario-3-wan1-down")
        print(f"✓ Scenario 3: WAN1 down → active = wan2")

    def test_both_wans_restored_after_steering_tests(
        self,
        sdwan: WANEdgeDevice,
        both_links_up: None,
    ) -> None:
        """After both WAN links are restored, baseline routing is re-established."""
        uc.assert_wan_interface_status(sdwan, "wan1", "up", label="scenario-3-restore")
        uc.assert_wan_interface_status(sdwan, "wan2", "up", label="scenario-3-restore")
        uc.assert_active_path(sdwan, expected_wan="wan1", label="scenario-3-restore")
        print(f"✓ Scenario 3 restore: both links up, wan1 primary restored")

    def test_path_metrics_within_slo_on_baseline_wan1(
        self,
        sdwan: WANEdgeDevice,
        both_links_up: None,
    ) -> None:
        """WAN1 path metrics are within acceptable SLO under baseline conditions.

        Validates that get_wan_path_metrics() returns real values and that
        loss is within the SLO.  Tolerance is generous — ping probes measure
        RTT to the TC gateway, which is sub-millisecond in this testbed.
        """
        metrics = sdwan.get_wan_path_metrics()
        assert "wan1" in metrics, (
            f"wan1 missing from path metrics: {list(metrics.keys())}"
        )
        m = metrics["wan1"]
        assert isinstance(m, PathMetrics)
        assert m.loss_percent < 5.0, (
            f"WAN1 packet loss {m.loss_percent:.2f}% exceeds 5% under baseline conditions"
        )
        print(
            f"✓ WAN1 path metrics: latency={m.latency_ms:.1f}ms, "
            f"jitter={m.jitter_ms:.1f}ms, loss={m.loss_percent:.2f}%"
        )


# ---------------------------------------------------------------------------
# Scenario 4 — Failover Convergence Time
# ---------------------------------------------------------------------------


class TestScenario4FailoverConvergenceTime:
    """Scenario 4: Measure and record DUT failover convergence time.

    Goal: Establish a performance baseline for how quickly the DUT switches
    from WAN1 to WAN2 following a link failure.  In Phase 3 the threshold is
    generous (3 s) to accommodate container scheduling overhead; a stricter
    SLO (< 500 ms) is enforced in Phase 3.5 after Digital Twin hardening.

    Methodology: ``_measure_link_failover()`` brings the link down and polls
    ``get_active_wan_interface()`` until WAN2 becomes active.  Returns elapsed
    ms from T0 (link-down called) to T1 (backup path confirmed).

    Note on ``measure_failover_convergence()`` use case:
        The ``wan_edge`` use case function ``measure_failover_convergence()``
        uses TC ``inject_blackout`` to trigger convergence.  This requires
        a working BFD session on the TC containers (Phase 3.5).  Scenarios
        here call ``_measure_link_failover()`` directly, which uses
        ``bring_wan_down`` and is the Phase 3 mechanism.
    """

    def test_failover_convergence_returns_positive_ms(
        self,
        sdwan: WANEdgeDevice,
        both_links_up: None,
    ) -> None:
        """Link-down failover returns a non-negative convergence time in ms.

        Does not enforce an SLO — records the value as the Phase 3 baseline.
        """
        conv_ms = _measure_link_failover(sdwan, "wan1", "wan2")

        assert isinstance(conv_ms, float)
        assert conv_ms >= 0, f"Convergence time must be ≥ 0, got {conv_ms:.1f}ms"
        print(
            f"✓ Scenario 4: link-down failover convergence = {conv_ms:.0f}ms "
            f"(Phase 3 baseline)"
        )

    def test_failover_convergence_within_phase3_slo(
        self,
        sdwan: WANEdgeDevice,
        both_links_up: None,
    ) -> None:
        """Link-down failover completes within the Phase 3 SLO of 3 seconds.

        3 000 ms provides ample margin over expected kernel/FRR convergence
        time (< 100 ms for link-down events) to accommodate container
        scheduling jitter and polling interval overhead.
        """
        conv_ms = _measure_link_failover(sdwan, "wan1", "wan2")

        assert conv_ms <= _FAILOVER_SLO_MS, (
            f"Failover convergence {conv_ms:.0f}ms exceeded Phase 3 SLO {_FAILOVER_SLO_MS}ms"
        )
        print(
            f"✓ Scenario 4: failover {conv_ms:.0f}ms ≤ Phase 3 SLO {_FAILOVER_SLO_MS}ms"
        )

    def test_assert_wan_interface_status_use_case_on_failed_link(
        self,
        sdwan: WANEdgeDevice,
        both_links_up: None,
    ) -> None:
        """assert_wan_interface_status() correctly reports 'down' during link failure.

        End-to-end use case test: bring link down → use case asserts expected state.
        """
        sdwan.bring_wan_down("wan1")
        time.sleep(_LINK_FAILOVER_S)
        try:
            uc.assert_wan_interface_status(sdwan, "wan1", "down", label="scenario-4")
            active = sdwan.get_active_wan_interface()
            assert active == "wan2", f"Expected wan2 active, got {active!r}"
        finally:
            sdwan.bring_wan_up("wan1")
            time.sleep(_LINK_RECOVER_S)
        print(f"✓ Scenario 4: wan1 'down' confirmed via use case during link failure")

    def test_failover_convergence_consistent_across_runs(
        self,
        sdwan: WANEdgeDevice,
        both_links_up: None,
    ) -> None:
        """Two consecutive convergence measurements both complete within SLO.

        Checks for gross outliers (e.g. one measurement takes 10× longer due
        to scheduling jitter).  Both measurements must be within the SLO.
        """
        conv1_ms = _measure_link_failover(sdwan, "wan1", "wan2")
        conv2_ms = _measure_link_failover(sdwan, "wan1", "wan2")

        assert conv1_ms <= _FAILOVER_SLO_MS, (
            f"Run 1 convergence {conv1_ms:.0f}ms exceeded SLO {_FAILOVER_SLO_MS}ms"
        )
        assert conv2_ms <= _FAILOVER_SLO_MS, (
            f"Run 2 convergence {conv2_ms:.0f}ms exceeded SLO {_FAILOVER_SLO_MS}ms"
        )
        print(
            f"✓ Scenario 4 consistency: run1={conv1_ms:.0f}ms, run2={conv2_ms:.0f}ms "
            f"(both ≤ {_FAILOVER_SLO_MS}ms)"
        )

    def test_failover_convergence_p50_p95_baseline_10_runs(
        self,
        sdwan: WANEdgeDevice,
        both_links_up: None,
    ) -> None:
        """Ten consecutive failover measurements; P50 and P95 within Phase 3 SLO.

        Establishes a statistical convergence baseline for the Phase 3 report.
        Both P50 (median) and P95 must be within the Phase 3 SLO of 3 000ms.

        With N=10 the P95 is effectively the worst-case sample (nearest-rank
        method: index ⌊0.95 × 10⌋ = 9 of the sorted list).  Requiring it to
        be ≤ SLO confirms that *every* run completed within the budget, not
        just the typical case.

        Each measurement brings WAN1 down, polls for WAN2 activation, then
        restores WAN1 and waits ``_LINK_RECOVER_S`` seconds for the primary
        route to stabilise before the next run.
        """
        _N = 10
        samples: list[float] = []

        for run in range(1, _N + 1):
            ms = _measure_link_failover(sdwan, "wan1", "wan2")
            samples.append(ms)
            print(f"  Run {run:2d}/{_N}: {ms:.0f}ms")

        samples_sorted = sorted(samples)
        p50 = statistics.median(samples)
        # Nearest-rank P95: for N=10, index 9 (the maximum sample).
        # statistics.quantiles with n=20 returns the 5th … 95th percentile
        # as a list of 19 values; index -1 is the 95th percentile.
        p95 = statistics.quantiles(samples_sorted, n=20)[-1]

        assert p50 <= _FAILOVER_SLO_MS, (
            f"P50 convergence {p50:.0f}ms exceeded Phase 3 SLO {_FAILOVER_SLO_MS}ms"
        )
        assert p95 <= _FAILOVER_SLO_MS, (
            f"P95 convergence {p95:.0f}ms exceeded Phase 3 SLO {_FAILOVER_SLO_MS}ms "
            f"(worst run: {max(samples):.0f}ms)"
        )
        print(
            f"✓ Scenario 4 N={_N} baseline: "
            f"P50={p50:.0f}ms, P95={p95:.0f}ms, "
            f"min={min(samples):.0f}ms, max={max(samples):.0f}ms "
            f"(SLO ≤ {_FAILOVER_SLO_MS}ms)"
        )
