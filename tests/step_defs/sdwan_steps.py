"""Step definitions for SD-WAN WAN failover scenarios.

Thin wrappers around boardfarm3 use_cases: wan_edge, traffic_control, and qoe.
All device interaction is delegated to use_cases — no direct device calls.
"""

from __future__ import annotations

import time

from pytest_bdd import given, parsers, then, when

from boardfarm3.lib.qoe import MeasurementSpec
from boardfarm3.use_cases import qoe as qoe_use_cases
from boardfarm3.use_cases import traffic_control as tc_use_cases
from boardfarm3.use_cases import traffic_generator as tg_use_cases
from boardfarm3.use_cases import wan_edge as wan_edge_use_cases

# Measurement specs for UC-SDWAN-02 page-load SLO testing.
# Uses browser 'load' event (Navigation Timing) with 60s timeout —
# matches the requirement's TTFB + total load time criteria.
PAGE_LOAD_SLO_SPEC = MeasurementSpec(
    tool="browser", completion="load", timeout_ms=60000
)

PRODUCTIVITY_URLS = {
    "http": "http://172.16.0.10:8080/",
    "https": "https://172.16.0.10/",
}

APP_CONFIG = {
    "productivity": {
        "measure": "measure_productivity",
        "assert_slo": "assert_productivity_slo",
        "url": "http://172.16.0.10:8080/",
        "spec": MeasurementSpec(tool="browser", completion="networkidle"),
        "slo_kwargs": {
            "max_ttfb_ms": 200,
            "max_load_time_ms": 15000,
        },
    },
    "streaming": {
        "measure": "measure_streaming",
        "assert_slo": "assert_streaming_slo",
        "url": "http://172.16.0.11:8081/hls/default/index.m3u8",
        "spec": MeasurementSpec(
            tool="http_client", completion="duration", duration_s=15
        ),
        "slo_kwargs": {
            "max_startup_time_ms": 5000,
            "max_rebuffer_ratio": 0.0,
        },
    },
    "conferencing": {
        "measure": "measure_conferencing",
        "assert_slo": "assert_conferencing_slo",
        "url": "wss://172.16.0.12:8443/room",
        "spec": MeasurementSpec(
            tool="webrtc", completion="duration", duration_s=10
        ),
        "slo_kwargs": {
            "min_mos": 3.5,
        },
    },
}


# ---------------------------------------------------------------------------
# Background / preparation
# ---------------------------------------------------------------------------


@given(
    "the SD-WAN appliance is operational with dual WAN connectivity"
)
def sdwan_appliance_operational(bf_context):
    """Discover and store all SDWAN devices from the device manager."""
    bf_context.sdwan_appliance = wan_edge_use_cases.get_wan_edge()
    bf_context.wan1_tc = tc_use_cases.get_traffic_controller(
        "wan1_tc"
    )
    bf_context.wan2_tc = tc_use_cases.get_traffic_controller(
        "wan2_tc"
    )
    bf_context.lan_client = qoe_use_cases.get_qoe_client()
    print(
        "✓ SD-WAN devices discovered:"
        " appliance, wan1_tc, wan2_tc, lan_client"
    )


@given(
    parsers.parse(
        'the network conditions are set to "{preset_name}"'
        " on all WAN links"
    )
)
def network_conditions_set_to_preset(
    bf_context, preset_name, boardfarm_config
):
    """Apply a named impairment preset to both WAN traffic controllers."""
    tc_use_cases.apply_preset(
        bf_context.wan1_tc, preset_name, boardfarm_config
    )
    tc_use_cases.apply_preset(
        bf_context.wan2_tc, preset_name, boardfarm_config
    )
    print(
        f'✓ Network conditions set to "{preset_name}"'
        " on all WAN links"
    )

    yield

    for tc in (bf_context.wan1_tc, bf_context.wan2_tc):
        try:
            tc_use_cases.clear_impairment(tc)
        except Exception as exc:  # noqa: BLE001
            print(f"⚠ Could not clear impairment: {exc}")


# ---------------------------------------------------------------------------
# Single-WAN preparation (actor: network operations)
# ---------------------------------------------------------------------------


@given(
    parsers.parse(
        "the appliance is configured for single-WAN"
        ' operation on "{active_wan}"'
    )
)
def appliance_configured_single_wan(bf_context, active_wan):
    """Admin-down all WAN links except the active one to simulate single-WAN.

    Discovers all WAN interfaces from the appliance, then brings down every
    interface except active_wan via ``edge.bring_wan_down()``.  This makes
    the router's SLA daemon see the interface as DOWN immediately, so it
    never attempts to route through it.

    Teardown brings the interfaces back up so subsequent scenarios see full
    dual-WAN connectivity again.
    """
    edge = bf_context.sdwan_appliance
    all_wans = list(edge.get_wan_interface_status().keys())

    if active_wan not in all_wans:
        raise ValueError(
            f"Active WAN {active_wan!r} not found."
            f" Available: {all_wans}"
        )

    # Ensure all WANs are UP and routing is converged before blocking.
    # A previous scenario's teardown may have just restored interfaces;
    # FRR needs time to re-install routes (ValueError: No route).
    for wan in all_wans:
        try:
            edge.bring_wan_up(wan)
        except Exception:  # noqa: BLE001
            pass  # already up is fine
    _wait_for_routing(edge, active_wan, timeout_s=30)

    blocked_wans = [w for w in all_wans if w != active_wan]
    for wan in blocked_wans:
        edge.bring_wan_down(wan)

    # Wait for the SLA daemon to converge to the active WAN only
    _wait_for_routing(edge, active_wan, timeout_s=15)

    bf_context.active_wan = active_wan
    bf_context.blocked_wans = blocked_wans
    print(
        f"✓ Single-WAN mode: {active_wan} active,"
        f" blocked: {blocked_wans}"
    )

    yield

    for wan in blocked_wans:
        try:
            edge.bring_wan_up(wan)
        except Exception as exc:  # noqa: BLE001
            print(
                f"⚠ Could not restore {wan}: {exc}"
            )


@given(
    parsers.parse(
        'the network conditions on the active WAN link'
        ' are set to "{preset_name}"'
    )
)
def network_conditions_set_on_active_wan(
    bf_context, preset_name, boardfarm_config
):
    """Apply a named impairment preset to only the active WAN link's TC."""
    active_wan = bf_context.active_wan
    tc = _get_tc_for_wan(bf_context, active_wan)
    tc_use_cases.apply_preset(tc, preset_name, boardfarm_config)
    print(
        f'✓ Network conditions set to "{preset_name}"'
        f" on {active_wan}"
    )

    yield

    try:
        tc_use_cases.clear_impairment(tc)
    except Exception as exc:  # noqa: BLE001
        print(
            f"⚠ Could not clear impairment on {active_wan}: {exc}"
        )


# ---------------------------------------------------------------------------
# Traffic generator discovery and operations (actor: network operations)
# ---------------------------------------------------------------------------


@given(
    "traffic generators are available on both sides"
    " of the appliance"
)
def traffic_generators_available(bf_context):
    """Discover LAN-side and north-side traffic generators."""
    bf_context.lan_traffic_gen = tg_use_cases.get_traffic_generator(
        "lan_traffic_gen"
    )
    bf_context.north_traffic_gen = tg_use_cases.get_traffic_generator(
        "north_traffic_gen"
    )
    print(
        "✓ Traffic generators discovered:"
        " lan_traffic_gen, north_traffic_gen"
    )


@when(
    parsers.parse(
        "network operations starts {bandwidth:d} Mbps of"
        " best-effort upstream background traffic"
        " through the appliance"
    )
)
def network_ops_starts_upstream_traffic(bf_context, bandwidth):
    """Start upstream best-effort traffic from LAN to north side."""
    flow_id = tg_use_cases.saturate_wan_link(
        source=bf_context.lan_traffic_gen,
        destination=bf_context.north_traffic_gen,
        link_bandwidth_mbps=bandwidth / 0.85,
        dscp=0,
        utilisation_pct=0.85,
        duration_s=120,
    )
    bf_context.upstream_flow_id = flow_id
    print(
        f"✓ Upstream background traffic started:"
        f" {bandwidth} Mbps BE (flow {flow_id})"
    )

    yield

    try:
        tg_use_cases.stop_traffic(
            bf_context.lan_traffic_gen, flow_id
        )
    except Exception as exc:  # noqa: BLE001
        print(f"⚠ Could not stop traffic flow {flow_id}: {exc}")


@when(
    "network operations stops the upstream background traffic"
)
def network_ops_stops_upstream_traffic(bf_context):
    """Stop the upstream background traffic flow and collect results."""
    result = tg_use_cases.stop_traffic(
        bf_context.lan_traffic_gen,
        bf_context.upstream_flow_id,
    )
    bf_context.upstream_traffic_result = result
    print(
        f"✓ Upstream background traffic stopped"
        f" (sent: {result.sent_mbps:.1f} Mbps,"
        f" loss: {result.loss_percent:.2f}%)"
    )


# ---------------------------------------------------------------------------
# WAN link status verification (actor: network operations)
# ---------------------------------------------------------------------------


@given(
    "network operations verifies that both WAN links"
    " are in UP state"
)
@then(
    "network operations verifies that both WAN links"
    " are in UP state"
)
def network_ops_verifies_wan_links_up(bf_context):
    """Assert both WAN1 and WAN2 are in UP state."""
    edge = bf_context.sdwan_appliance
    wan_edge_use_cases.assert_wan_interface_status(
        edge, "wan1", "up"
    )
    wan_edge_use_cases.assert_wan_interface_status(
        edge, "wan2", "up"
    )
    print("✓ Both WAN links are in UP state")


@given(
    parsers.parse(
        'network operations verifies that "{wan_link}"'
        " is the active forwarding path"
    )
)
def network_ops_verifies_active_path_given(
    bf_context, wan_link
):
    """Wait for the device to settle on the expected WAN path.

    Used as a precondition: the SLA daemon may still be
    re-converging after a pristine reset, so we poll rather
    than assert instantly.
    """
    edge = bf_context.sdwan_appliance
    wan_edge_use_cases.wait_for_path_switch(
        edge, wan_link, timeout_ms=10_000
    )
    print(f"✓ {wan_link} is the active forwarding path")


@then(
    parsers.parse(
        'network operations verifies that "{wan_link}"'
        " is the active forwarding path"
    )
)
def network_ops_verifies_active_path(bf_context, wan_link):
    """Assert the device is forwarding on the specified WAN link."""
    edge = bf_context.sdwan_appliance
    wan_edge_use_cases.assert_active_path(edge, wan_link)
    print(f"✓ {wan_link} is the active forwarding path")


# ---------------------------------------------------------------------------
# Application session (actor: remote worker)
# Parameterized by app_type (productivity | streaming | conferencing)
# ---------------------------------------------------------------------------


@when(
    parsers.parse(
        'the remote worker starts a "{app_type}" session'
        " through the appliance"
    )
)
def remote_worker_starts_session(bf_context, app_type):
    """Start an application session and record the baseline.

    Uses the default wait_until strategy from APP_CONFIG (networkidle
    for session continuity tests).  For page-load SLO tests under
    impaired conditions, use ``remote_worker_loads_productivity_page``
    which uses wait_until="load".
    """
    cfg = _get_app_config(app_type)
    client = bf_context.lan_client
    measure_fn = getattr(qoe_use_cases, cfg["measure"])
    result = measure_fn(
        client, cfg["url"], spec=cfg.get("spec")
    )
    bf_context.app_session_baseline = result
    bf_context.app_type = app_type
    bf_context.app_config = cfg
    print(f"✓ {app_type} session started")


@when(
    parsers.parse(
        'the remote worker confirms the "{app_type}"'
        " session is responsive"
    )
)
def remote_worker_confirms_responsive(bf_context, app_type):
    """Assert the baseline measurement meets SLOs for this app type."""
    cfg = _get_app_config(app_type)
    result = bf_context.app_session_baseline
    assert_slo_fn = getattr(qoe_use_cases, cfg["assert_slo"])
    assert_slo_fn(result, **cfg["slo_kwargs"])
    print(f"✓ {app_type} session responsive")


@when(
    "the remote worker loads the productivity page"
    " through the appliance"
)
def remote_worker_loads_productivity_page(bf_context):
    """Measure page-load timing using wait_until='load'.

    Uses the browser 'load' event (Navigation Timing loadEventEnd) instead
    of 'networkidle'.  This matches the UC-SDWAN-02 requirement which
    defines success as TTFB and total load time — metrics available at the
    load event.  More resilient to slow sub-resource loading under impaired
    WAN conditions.

    Timeout is set to 60s (2x the worst-case satellite SLO of 12000ms +
    margin for retransmissions under high loss).
    """
    cfg = _get_app_config("productivity")
    client = bf_context.lan_client
    result = qoe_use_cases.measure_productivity(
        client, cfg["url"], spec=PAGE_LOAD_SLO_SPEC
    )
    bf_context.app_session_baseline = result
    bf_context.app_type = "productivity"
    bf_context.app_config = cfg
    print(
        f"✓ Productivity page loaded"
        f" (TTFB: {result.ttfb_ms}ms,"
        f" load: {result.load_time_ms}ms,"
        f" success: {result.success})"
    )


@then(
    parsers.parse(
        "the remote worker confirms the productivity"
        " page loads within {max_ttfb:d} ms TTFB"
        " and {max_load_time:d} ms total"
    )
)
def remote_worker_confirms_productivity_slo(
    bf_context, max_ttfb, max_load_time
):
    """Assert the productivity baseline meets explicit SLO thresholds."""
    result = bf_context.app_session_baseline
    qoe_use_cases.assert_productivity_slo(
        result,
        max_ttfb_ms=max_ttfb,
        max_load_time_ms=max_load_time,
    )
    print(
        f"✓ Productivity SLO met:"
        f" TTFB {result.ttfb_ms:.0f}ms ≤ {max_ttfb}ms,"
        f" load {result.load_time_ms:.0f}ms ≤ {max_load_time}ms"
    )


@when(
    parsers.parse(
        'the remote worker starts a "{app_type}" session'
        ' over "{scheme}" through the appliance'
    )
)
def remote_worker_starts_session_over_scheme(
    bf_context, app_type, scheme
):
    """Start an application session using a scheme-specific URL."""
    cfg = _get_app_config(app_type)
    url = PRODUCTIVITY_URLS.get(scheme)
    if url is None:
        raise ValueError(
            f"Unknown scheme {scheme!r}."
            f" Supported: {list(PRODUCTIVITY_URLS)}"
        )
    client = bf_context.lan_client
    measure_fn = getattr(qoe_use_cases, cfg["measure"])
    result = measure_fn(
        client, url, spec=PAGE_LOAD_SLO_SPEC
    )
    bf_context.app_session_baseline = result
    bf_context.app_type = app_type
    bf_context.app_config = cfg
    print(f"✓ {app_type} session started over {scheme}")


@then(
    parsers.parse(
        "the remote worker confirms the negotiated"
        ' protocol is "{expected_protocol}"'
    )
)
def remote_worker_confirms_protocol(
    bf_context, expected_protocol
):
    """Assert the negotiated HTTP protocol matches the expected value."""
    result = bf_context.app_session_baseline
    actual = result.protocol
    assert actual is not None, (
        f"Protocol not reported (result.protocol is None)."
        f" Expected: {expected_protocol!r}"
    )
    assert actual == expected_protocol, (
        f"Protocol mismatch: got {actual!r},"
        f" expected {expected_protocol!r}"
    )
    print(
        f"✓ Negotiated protocol is {actual!r}"
    )


@then(
    parsers.parse(
        'the remote worker confirms the "{app_type}"'
        " session remains functional"
        " within the continuity SLO"
    )
)
def remote_worker_confirms_session_functional(
    bf_context, app_type
):
    """Re-measure the application and assert the continuity SLO."""
    cfg = _get_app_config(app_type)
    client = bf_context.lan_client
    measure_fn = getattr(qoe_use_cases, cfg["measure"])
    result = measure_fn(
        client, cfg["url"], spec=cfg.get("spec")
    )
    assert_slo_fn = getattr(qoe_use_cases, cfg["assert_slo"])
    assert_slo_fn(result, **cfg["slo_kwargs"])
    bf_context.last_qoe_result = result
    print(f"✓ {app_type} session functional within continuity SLO")


# ---------------------------------------------------------------------------
# Application unreachable (actor: remote worker)
# ---------------------------------------------------------------------------


@when(
    "the remote worker navigates to an unreachable"
    " application URL"
)
def remote_worker_navigates_unreachable(bf_context):
    """Attempt to load a productivity page at an unreachable URL."""
    client = bf_context.lan_client
    result = qoe_use_cases.measure_productivity(
        client, "http://192.0.2.1:9999/unreachable"
    )
    bf_context.last_qoe_result = result
    print(
        f"✓ Navigation to unreachable URL completed"
        f" (success={result.success})"
    )


@then(
    "the remote worker's browser reports a connection failure"
)
def remote_worker_browser_reports_failure(bf_context):
    """Assert the browser reported a connection failure."""
    result = bf_context.last_qoe_result
    qoe_use_cases.assert_request_blocked(
        result, label="unreachable application"
    )
    print("✓ Browser reported connection failure as expected")


# ---------------------------------------------------------------------------
# WAN link impairment (failure injection)
# ---------------------------------------------------------------------------


@when(
    parsers.parse(
        '"{wan_link}" experiences a complete link failure'
    )
)
def wan_link_complete_failure(bf_context, wan_link):
    """Inject sustained 100% packet loss on the specified WAN link."""
    tc = _get_tc_for_wan(bf_context, wan_link)
    from boardfarm3.lib.traffic_control import ImpairmentProfile

    tc_use_cases.set_impairment_profile(
        tc,
        ImpairmentProfile(
            latency_ms=0,
            jitter_ms=0,
            loss_percent=100.0,
            bandwidth_limit_mbps=None,
        ),
    )
    bf_context.failure_start_time = time.monotonic()
    bf_context.impaired_wan = wan_link
    print(
        f"✓ {wan_link} now experiencing complete link failure"
        " (100% loss)"
    )

    yield

    try:
        tc_use_cases.clear_impairment(tc)
    except Exception as exc:  # noqa: BLE001
        print(f"⚠ Could not clear impairment on {wan_link}: {exc}")


@when(
    parsers.parse(
        '"{wan_link}" experiences degraded conditions'
        ' consistent with "{preset_name}"'
    )
)
def wan_link_degraded(
    bf_context, wan_link, preset_name, boardfarm_config
):
    """Apply a degradation preset to the specified WAN link."""
    tc = _get_tc_for_wan(bf_context, wan_link)
    tc_use_cases.apply_preset(tc, preset_name, boardfarm_config)
    bf_context.failure_start_time = time.monotonic()
    bf_context.impaired_wan = wan_link
    print(
        f"✓ {wan_link} now experiencing degraded conditions"
        f' ("{preset_name}")'
    )

    yield

    try:
        tc_use_cases.clear_impairment(tc)
    except Exception as exc:  # noqa: BLE001
        print(f"⚠ Could not clear impairment on {wan_link}: {exc}")


@when(
    parsers.parse(
        '"{wan_link}" recovers and returns to healthy state'
    )
)
def wan_link_recovers(bf_context, wan_link):
    """Clear all impairment on the specified WAN link."""
    tc = _get_tc_for_wan(bf_context, wan_link)
    tc_use_cases.clear_impairment(tc)
    bf_context.recovery_start_time = time.monotonic()
    print(f"✓ {wan_link} recovered — impairment cleared")


# ---------------------------------------------------------------------------
# Failover / failback convergence
# ---------------------------------------------------------------------------


@then(
    parsers.parse(
        "the appliance detects the failure and converges to"
        ' "{expected_wan}" within {max_ms:d} ms'
    )
)
def appliance_converges_within_slo(
    bf_context, expected_wan, max_ms
):
    """Wait for the device to switch to expected_wan within SLO."""
    edge = bf_context.sdwan_appliance
    elapsed_ms = wan_edge_use_cases.wait_for_path_switch(
        edge, expected_wan, timeout_ms=max_ms
    )
    bf_context.convergence_ms = elapsed_ms
    print(
        f"✓ Convergence to {expected_wan}: {elapsed_ms:.0f}ms"
        f" (SLO: {max_ms}ms)"
    )


@then(
    parsers.parse(
        'the appliance steers traffic to "{expected_wan}"'
    )
)
def appliance_steers_traffic(bf_context, expected_wan):
    """Wait for the device to steer traffic to expected_wan."""
    edge = bf_context.sdwan_appliance
    elapsed_ms = wan_edge_use_cases.wait_for_path_switch(
        edge, expected_wan, timeout_ms=10_000
    )
    print(
        f"✓ Appliance steered traffic to {expected_wan}"
        f" ({elapsed_ms:.0f}ms)"
    )


@then(
    parsers.parse(
        'the appliance fails back to "{wan_link}"'
        " as the preferred path"
    )
)
def appliance_fails_back(bf_context, wan_link):
    """Wait for the device to fail back to the preferred WAN link."""
    edge = bf_context.sdwan_appliance
    elapsed_ms = wan_edge_use_cases.wait_for_path_switch(
        edge, wan_link, timeout_ms=30_000
    )
    bf_context.failback_ms = elapsed_ms
    print(
        f"✓ Appliance failed back to {wan_link}"
        f" ({elapsed_ms:.0f}ms)"
    )


# ---------------------------------------------------------------------------
# Helpers (private)
# ---------------------------------------------------------------------------


def _get_app_config(app_type: str) -> dict:
    """Return the APP_CONFIG entry for the given application type."""
    if app_type not in APP_CONFIG:
        raise ValueError(
            f"Unknown application type {app_type!r}."
            f" Supported: {list(APP_CONFIG)}"
        )
    return APP_CONFIG[app_type]


def _wait_for_routing(edge, expected_wan: str, timeout_s: int = 30):
    """Poll until the router has routes and the active path is expected_wan.

    Tolerates ValueError (no route yet) during the polling period.
    """
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        try:
            if edge.get_active_wan_interface() == expected_wan:
                return
        except (ValueError, AssertionError):
            pass  # routes not installed yet
        time.sleep(0.5)
    # Final attempt — let it raise on failure
    wan_edge_use_cases.wait_for_path_switch(
        edge, expected_wan, timeout_ms=5_000
    )


def _get_tc_for_wan(bf_context, wan_link: str):
    """Resolve the TrafficController for a logical WAN link name."""
    mapping = {
        "wan1": bf_context.wan1_tc,
        "wan2": bf_context.wan2_tc,
    }
    tc = mapping.get(wan_link)
    if tc is None:
        raise ValueError(
            f"No TrafficController mapped for WAN link"
            f" {wan_link!r}. Available: {list(mapping)}"
        )
    return tc
