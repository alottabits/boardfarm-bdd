"""Pytest validation for LinuxSDWANRouter via boardfarm fixtures.

Validates all WANEdgeDevice template methods implemented by LinuxSDWANRouter.
Uses boardfarm device_manager/devices fixtures - requires full boardfarm args.

Run from boardfarm-bdd/ with venv activated and linux-sdwan-router running:

    pytest tests/dc_methods/test_linux_sdwan_router.py -v \\
        --board-name sdwan \\
        --env-config bf_config/bf_env_sdwan.json \\
        --inventory-config bf_config/bf_config_sdwan.json \\
        --legacy --skip-boot --save-console-logs ""
"""

from __future__ import annotations

from typing import cast

import pytest

from boardfarm3.templates.wan_edge import WANEdgeDevice


def _require_sdwan(sdwan: WANEdgeDevice | None) -> WANEdgeDevice:
    """Skip test if sdwan device is not available (e.g. wrong board config)."""
    if sdwan is None:
        pytest.skip("sdwan device not in testbed (use --board-name sdwan)")
    return cast(WANEdgeDevice, sdwan)


# --- Read-only method tests ---


def test_get_active_wan_interface(sdwan: WANEdgeDevice | None) -> None:
    """Validate get_active_wan_interface returns logical label (wan1 or wan2)."""
    dut = _require_sdwan(sdwan)
    active = dut.get_active_wan_interface()
    assert active in ("wan1", "wan2"), f"Expected wan1/wan2, got {active!r}"
    print(f"✓ get_active_wan_interface: {active}")


def test_get_active_wan_interface_with_flow_dst(sdwan: WANEdgeDevice | None) -> None:
    """Validate get_active_wan_interface with flow_dst parameter."""
    dut = _require_sdwan(sdwan)
    active = dut.get_active_wan_interface(flow_dst="172.16.0.10")
    assert active in ("wan1", "wan2"), f"Expected wan1/wan2, got {active!r}"
    print(f"✓ get_active_wan_interface(flow_dst='172.16.0.10'): {active}")


def test_get_wan_interface_status(sdwan: WANEdgeDevice | None) -> None:
    """Validate get_wan_interface_status returns LinkStatus for each WAN."""
    dut = _require_sdwan(sdwan)
    status = dut.get_wan_interface_status()
    assert "wan1" in status, "wan1 missing from status"
    assert "wan2" in status, "wan2 missing from status"
    for label in ("wan1", "wan2"):
        s = status[label]
        assert s.state in ("up", "down"), (
            f"{label} state should be up/down, got {s.state!r}"
        )
        assert hasattr(s, "ip_address")
        assert hasattr(s, "name")
    print(
        f"✓ get_wan_interface_status: wan1={status['wan1'].state}, "
        f"wan2={status['wan2'].state}"
    )


def test_get_routing_table(sdwan: WANEdgeDevice | None) -> None:
    """Validate get_routing_table returns RouteEntry list."""
    dut = _require_sdwan(sdwan)
    routes = dut.get_routing_table()
    assert isinstance(routes, list), "Expected list of RouteEntry"
    assert len(routes) > 0, "Routing table should not be empty"
    default = next((r for r in routes if r.destination == "0.0.0.0/0"), None)
    assert default is not None, "Default route 0.0.0.0/0 expected"
    assert hasattr(default, "gateway") and hasattr(default, "interface")
    print(
        f"✓ get_routing_table: {len(routes)} entries, "
        f"default via {default.gateway} dev {default.interface}"
    )


def test_get_wan_path_metrics(sdwan: WANEdgeDevice | None) -> None:
    """Validate get_wan_path_metrics returns PathMetrics per WAN."""
    dut = _require_sdwan(sdwan)
    metrics = dut.get_wan_path_metrics()
    assert "wan1" in metrics, "wan1 missing from metrics"
    assert "wan2" in metrics, "wan2 missing from metrics"
    for label in ("wan1", "wan2"):
        m = metrics[label]
        assert hasattr(m, "latency_ms") and hasattr(m, "loss_percent")
        assert hasattr(m, "jitter_ms") and hasattr(m, "link_name")
    m1 = metrics["wan1"].latency_ms
    m2 = metrics["wan2"].latency_ms
    print(
        f"✓ get_wan_path_metrics: wan1 latency={m1:.1f}ms, "
        f"wan2 latency={m2:.1f}ms"
    )


def test_get_telemetry(sdwan: WANEdgeDevice | None) -> None:
    """Validate get_telemetry returns uptime, cpu, memory."""
    dut = _require_sdwan(sdwan)
    tel = dut.get_telemetry()
    assert "uptime_seconds" in tel, "uptime_seconds missing"
    assert "cpu_load_percent" in tel, "cpu_load_percent missing"
    assert "mem_used_percent" in tel, "mem_used_percent missing"
    assert tel["uptime_seconds"] >= 0
    assert 0 <= tel["cpu_load_percent"] <= 100
    assert 0 <= tel["mem_used_percent"] <= 100
    uptime = tel["uptime_seconds"]
    cpu = tel["cpu_load_percent"]
    mem = tel["mem_used_percent"]
    print(f"✓ get_telemetry: uptime={uptime:.0f}s, cpu={cpu:.1f}%, mem={mem:.1f}%")


def test_get_security_log_events(sdwan: WANEdgeDevice | None) -> None:
    """Validate get_security_log_events returns list (may be empty)."""
    dut = _require_sdwan(sdwan)
    events = dut.get_security_log_events(since_s=60)
    assert isinstance(events, list), "Expected list of events"
    print(f"✓ get_security_log_events: {len(events)} events in last 60s")


def test_properties(sdwan: WANEdgeDevice | None) -> None:
    """Validate nbi, gui, console properties."""
    dut = _require_sdwan(sdwan)
    assert dut.nbi is None, "Linux Router has no NBI"
    assert dut.gui is None, "Linux Router has no GUI"
    assert dut.console is not None, "Console should be available"
    print("✓ properties: nbi=None, gui=None, console=available")


# --- State-changing method tests (order matters, restore state) ---


def test_bring_wan_down_and_up(sdwan: WANEdgeDevice | None) -> None:
    """Validate bring_wan_down and bring_wan_up."""
    dut = _require_sdwan(sdwan)
    # Bring wan2 down
    dut.bring_wan_down("wan2")
    status = dut.get_wan_interface_status()
    assert status["wan2"].state == "down", "wan2 should be down"
    active = dut.get_active_wan_interface()
    assert active == "wan1", "Traffic should use wan1"
    print("✓ bring_wan_down(wan2): wan2 down, traffic on wan1")

    # Restore wan2
    dut.bring_wan_up("wan2")
    status = dut.get_wan_interface_status()
    assert status["wan2"].state == "up", "wan2 should be up after bring_wan_up"
    print("✓ bring_wan_up(wan2): wan2 restored")


def test_apply_and_remove_policy(sdwan: WANEdgeDevice | None) -> None:
    """Validate apply_policy and remove_policy (requires FRR PBR)."""
    dut = _require_sdwan(sdwan)
    policy = {
        "name": "test-validation-policy",
        "match": {"dst_prefix": "172.16.0.10/32"},
        "action": {"prefer_wan": "wan2"},
    }
    dut.apply_policy(policy)
    active = dut.get_active_wan_interface(flow_dst="172.16.0.10")
    assert active == "wan2", f"Policy should steer to wan2, got {active!r}"
    print("✓ apply_policy: traffic to 172.16.0.10 steered to wan2")

    dut.remove_policy("test-validation-policy")
    # After remove, default route applies (may be wan1 or wan2)
    active_after = dut.get_active_wan_interface(flow_dst="172.16.0.10")
    assert active_after in ("wan1", "wan2"), (
        f"Expected wan1/wan2 after remove, got {active_after!r}"
    )
    print("✓ remove_policy: policy removed")
