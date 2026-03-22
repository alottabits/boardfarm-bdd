"""Step definitions for SD-WAN WAN failover scenarios.

Thin wrappers around boardfarm3 use_cases: wan_edge, traffic_control, and qoe.
All device interaction is delegated to use_cases — no direct device calls.
"""

from __future__ import annotations

import time

from pytest_bdd import given, parsers, then, when

from boardfarm3.use_cases import qoe as qoe_use_cases
from boardfarm3.use_cases import traffic_control as tc_use_cases
from boardfarm3.use_cases import wan_edge as wan_edge_use_cases

APP_CONFIG = {
    "productivity": {
        "measure": "measure_productivity",
        "assert_slo": "assert_productivity_slo",
        "url": "http://172.16.0.10:8080/",
        "measure_kwargs": {},
        "slo_kwargs": {
            "max_ttfb_ms": 200,
            "max_load_time_ms": 15000,
        },
    },
    "streaming": {
        "measure": "measure_streaming",
        "assert_slo": "assert_streaming_slo",
        "url": "http://172.16.0.11:8081/hls/default/index.m3u8",
        "measure_kwargs": {"duration_s": 15},
        "slo_kwargs": {
            "max_startup_time_ms": 5000,
            "max_rebuffer_ratio": 0.0,
        },
    },
    "conferencing": {
        "measure": "measure_conferencing",
        "assert_slo": "assert_conferencing_slo",
        "url": "wss://172.16.0.12:8443/room",
        "measure_kwargs": {"duration_s": 10},
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
    dut = bf_context.sdwan_appliance
    wan_edge_use_cases.assert_wan_interface_status(
        dut, "wan1", "up"
    )
    wan_edge_use_cases.assert_wan_interface_status(
        dut, "wan2", "up"
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
    """Wait for the DUT to settle on the expected WAN path.

    Used as a precondition: the SLA daemon may still be
    re-converging after a pristine reset, so we poll rather
    than assert instantly.
    """
    dut = bf_context.sdwan_appliance
    wan_edge_use_cases.wait_for_path_switch(
        dut, wan_link, timeout_ms=10_000
    )
    print(f"✓ {wan_link} is the active forwarding path")


@then(
    parsers.parse(
        'network operations verifies that "{wan_link}"'
        " is the active forwarding path"
    )
)
def network_ops_verifies_active_path(bf_context, wan_link):
    """Assert the DUT is forwarding on the specified WAN link."""
    dut = bf_context.sdwan_appliance
    wan_edge_use_cases.assert_active_path(dut, wan_link)
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
    """Start an application session and record the baseline."""
    cfg = _get_app_config(app_type)
    client = bf_context.lan_client
    measure_fn = getattr(qoe_use_cases, cfg["measure"])
    result = measure_fn(
        client, cfg["url"], **cfg.get("measure_kwargs", {})
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
        client, cfg["url"], **cfg.get("measure_kwargs", {})
    )
    assert_slo_fn = getattr(qoe_use_cases, cfg["assert_slo"])
    assert_slo_fn(result, **cfg["slo_kwargs"])
    bf_context.last_qoe_result = result
    print(f"✓ {app_type} session functional within continuity SLO")


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
    """Wait for the DUT to switch to expected_wan within SLO."""
    dut = bf_context.sdwan_appliance
    elapsed_ms = wan_edge_use_cases.wait_for_path_switch(
        dut, expected_wan, timeout_ms=max_ms
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
    """Wait for the DUT to steer traffic to expected_wan."""
    dut = bf_context.sdwan_appliance
    elapsed_ms = wan_edge_use_cases.wait_for_path_switch(
        dut, expected_wan, timeout_ms=10_000
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
    """Wait for the DUT to fail back to the preferred WAN link."""
    dut = bf_context.sdwan_appliance
    elapsed_ms = wan_edge_use_cases.wait_for_path_switch(
        dut, wan_link, timeout_ms=30_000
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
