"""Pytest validation for PlaywrightQoEClient via boardfarm fixtures.

Validates all QoEClient template methods implemented by PlaywrightQoEClient.
Uses boardfarm device_manager/devices fixtures — requires full boardfarm args.

Tests exercise the device methods directly (NOT through the use-case layer) to
validate that the Playwright scripts run correctly on the ``lan-qoe-client`` container,
parse JSON output, and populate :class:`~boardfarm3.lib.qoe.QoEResult` correctly.

Run from boardfarm-bdd/ with venv activated and lan-qoe-client container running:

    pytest tests/dc_methods/test_playwright_qoe_client.py -v \\
        --board-name sdwan \\
        --env-config bf_config/bf_env_sdwan.json \\
        --inventory-config bf_config/bf_config_sdwan.json \\
        --legacy --skip-boot --save-console-logs ""

Prerequisites:
- ``lan-qoe-client`` container running (``docker compose -p boardfarm-bdd-sdwan ... up``)
- ``productivity-server`` container running (for productivity tests)
- ``streaming-server`` container running (for streaming tests)
- ``conf-server`` container running with pion (for conferencing tests — skip if absent)
- Raikou has injected eth-lan into the lan-qoe-client container
- Default route in lan-qoe-client via DUT LAN IP (192.168.10.1)
- Python venv with boardfarm3 and playwright installed

Service URLs (aligned with raikou/config_sdwan.json north-segment: 172.16.0.0/24):
- Productivity: http://172.16.0.10:8080/  (productivity-server nginx on north-segment)
- Streaming:    http://172.16.0.11:8081/hls/default/index.m3u8  (streaming-server HLS edge)
- Conferencing: ws://172.16.0.12:8443/session  (conf-server WSS, Phase 2+)
- Malicious:    172.16.0.20:4444  (malicious-host C2 listener, Phase 4+)
"""

from __future__ import annotations

import os
from typing import cast

import pytest

from boardfarm3.lib.qoe import QoEResult
from boardfarm3.templates.qoe_client import QoEClient

# ---------------------------------------------------------------------------
# Constants — adjust to match your testbed layout
# ---------------------------------------------------------------------------

_QOE_DEVICE_NAME: str = os.environ.get("QOE_DEVICE_NAME", "lan_qoe_client")

# URLs of services reachable through the DUT
# IPs match raikou/config_sdwan.json: north-segment is 172.16.0.0/24
# productivity-server and streaming-server nginx listen on port 8080
_PRODUCTIVITY_URL: str = os.environ.get(
    "PRODUCTIVITY_URL", "http://172.16.0.10:8080/"
)
_STREAMING_URL: str = os.environ.get(
    "STREAMING_URL", "http://172.16.0.11:8081/hls/default/index.m3u8"
)
_CONF_SESSION_URL: str = os.environ.get(
    "CONF_SESSION_URL", "ws://172.16.0.12:8443/session"
)

# Security test targets — malicious-host on north-segment (Phase 4+)
_BLOCKED_HOST: str = os.environ.get("BLOCKED_HOST", "172.16.0.20")
_BLOCKED_PORT: int = int(os.environ.get("BLOCKED_PORT", "4444"))

# Known-open port on the productivity server (nginx port 8080)
_ALLOWED_HOST: str = os.environ.get("ALLOWED_HOST", "172.16.0.10")
_ALLOWED_PORT: int = int(os.environ.get("ALLOWED_PORT", "8080"))


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _require_qoe_client(devices: object, name: str) -> QoEClient:
    """Return the QoEClient device or skip if unavailable."""
    dev = getattr(devices, name, None)
    if dev is None:
        pytest.skip(
            f"QoEClient device {name!r} not in testbed "
            "(use --board-name sdwan and ensure the lan-qoe-client container is running)"
        )
    return cast(QoEClient, dev)


@pytest.fixture()
def qoe(devices: object) -> QoEClient:
    """Yield the PlaywrightQoEClient device."""
    return _require_qoe_client(devices, _QOE_DEVICE_NAME)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _assert_result_type(result: object, label: str = "") -> None:
    """Assert that *result* is a QoEResult instance."""
    prefix = f"[{label}] " if label else ""
    assert isinstance(result, QoEResult), (
        f"{prefix}Expected QoEResult, got {type(result)}"
    )


# ---------------------------------------------------------------------------
# Tests: ip_address property
# ---------------------------------------------------------------------------


def test_ip_address_is_string(qoe: QoEClient) -> None:
    """ip_address returns a non-empty string."""
    addr = qoe.ip_address
    assert isinstance(addr, str), f"Expected str, got {type(addr)}"
    assert len(addr) > 0, "ip_address must be non-empty"
    print(f"✓ ip_address: {addr!r}")


def test_ip_address_matches_simulated_ip(qoe: QoEClient) -> None:
    """ip_address matches the simulated_ip from inventory config."""
    addr = qoe.ip_address
    # The inventory sets simulated_ip = "192.168.10.10"
    assert addr == "192.168.10.10", (
        f"ip_address expected '192.168.10.10', got {addr!r}"
    )
    print(f"✓ ip_address == simulated_ip: {addr!r}")


# ---------------------------------------------------------------------------
# Tests: measure_productivity
# ---------------------------------------------------------------------------


def test_measure_productivity_returns_qoe_result(qoe: QoEClient) -> None:
    """measure_productivity() returns a QoEResult instance."""
    result = qoe.measure_productivity(_PRODUCTIVITY_URL)
    _assert_result_type(result, "measure_productivity")
    print(f"✓ measure_productivity returned QoEResult: {result}")


def test_measure_productivity_success(qoe: QoEClient) -> None:
    """measure_productivity() to reachable URL returns success=True."""
    result = qoe.measure_productivity(_PRODUCTIVITY_URL)
    assert result.success is True, (
        f"Expected success=True for {_PRODUCTIVITY_URL!r}, got success=False"
    )
    print(f"✓ measure_productivity success=True for {_PRODUCTIVITY_URL!r}")


def test_measure_productivity_ttfb_positive(qoe: QoEClient) -> None:
    """measure_productivity() populates ttfb_ms as a positive number."""
    result = qoe.measure_productivity(_PRODUCTIVITY_URL)
    assert result.ttfb_ms is not None, "ttfb_ms is None (not measured)"
    assert result.ttfb_ms > 0, (
        f"ttfb_ms expected > 0, got {result.ttfb_ms}"
    )
    print(f"✓ ttfb_ms = {result.ttfb_ms:.1f} ms")


def test_measure_productivity_load_time_positive(qoe: QoEClient) -> None:
    """measure_productivity() populates load_time_ms as a positive number."""
    result = qoe.measure_productivity(_PRODUCTIVITY_URL)
    assert result.load_time_ms is not None, "load_time_ms is None (not measured)"
    assert result.load_time_ms > 0, (
        f"load_time_ms expected > 0, got {result.load_time_ms}"
    )
    print(f"✓ load_time_ms = {result.load_time_ms:.1f} ms")


def test_measure_productivity_load_time_ge_ttfb(qoe: QoEClient) -> None:
    """load_time_ms >= ttfb_ms (full load cannot be faster than first byte)."""
    result = qoe.measure_productivity(_PRODUCTIVITY_URL)
    if result.ttfb_ms is None or result.load_time_ms is None:
        pytest.skip("TTFB or load time not available")
    assert result.load_time_ms >= result.ttfb_ms, (
        f"load_time_ms ({result.load_time_ms:.1f}) < ttfb_ms ({result.ttfb_ms:.1f})"
    )
    print(f"✓ load_time_ms ({result.load_time_ms:.1f}) >= ttfb_ms ({result.ttfb_ms:.1f})")


def test_measure_productivity_unreachable_returns_failure(qoe: QoEClient) -> None:
    """measure_productivity() to an unreachable host returns success=False."""
    result = qoe.measure_productivity("http://192.0.2.1/")  # RFC 5737 TEST-NET — unroutable
    assert result.success is False, (
        "Expected success=False for unreachable URL, got success=True"
    )
    print("✓ measure_productivity unreachable URL → success=False")


def test_measure_productivity_non_streaming_fields_are_none(qoe: QoEClient) -> None:
    """Streaming and conferencing fields are None in a productivity result."""
    result = qoe.measure_productivity(_PRODUCTIVITY_URL)
    assert result.startup_time_ms is None, (
        f"startup_time_ms should be None, got {result.startup_time_ms}"
    )
    assert result.rebuffer_ratio is None, (
        f"rebuffer_ratio should be None, got {result.rebuffer_ratio}"
    )
    assert result.mos_score is None, (
        f"mos_score should be None, got {result.mos_score}"
    )
    print("✓ streaming/conferencing fields are None in productivity result")


# ---------------------------------------------------------------------------
# Tests: measure_streaming
# ---------------------------------------------------------------------------


def test_measure_streaming_returns_qoe_result(qoe: QoEClient) -> None:
    """measure_streaming() returns a QoEResult instance."""
    result = qoe.measure_streaming(_STREAMING_URL)
    _assert_result_type(result, "measure_streaming")
    print(f"✓ measure_streaming returned QoEResult: {result}")


def test_measure_streaming_success(qoe: QoEClient) -> None:
    """measure_streaming() to reachable manifest returns success=True."""
    result = qoe.measure_streaming(_STREAMING_URL)
    assert result.success is True, (
        f"Expected success=True for {_STREAMING_URL!r}, got success=False "
        "(ensure streaming-server is running)"
    )
    print(f"✓ measure_streaming success=True for {_STREAMING_URL!r}")


def test_measure_streaming_startup_time_positive(qoe: QoEClient) -> None:
    """measure_streaming() populates startup_time_ms > 0 on success."""
    result = qoe.measure_streaming(_STREAMING_URL)
    assert result.success is True, (
        f"Expected success=True for {_STREAMING_URL!r}, got success=False "
        "(ensure streaming-server is running and HLS content is ingested)"
    )
    assert result.startup_time_ms is not None, "startup_time_ms is None"
    assert result.startup_time_ms > 0, (
        f"startup_time_ms expected > 0, got {result.startup_time_ms}"
    )
    print(f"✓ startup_time_ms = {result.startup_time_ms:.1f} ms")


def test_measure_streaming_rebuffer_ratio_phase1(qoe: QoEClient) -> None:
    """Phase 1: rebuffer_ratio == 0.0 (live tracking not yet implemented)."""
    result = qoe.measure_streaming(_STREAMING_URL)
    assert result.success is True, (
        f"Expected success=True for {_STREAMING_URL!r}, got success=False "
        "(ensure streaming-server is running and HLS content is ingested)"
    )
    assert result.rebuffer_ratio is not None, "rebuffer_ratio is None"
    assert result.rebuffer_ratio == 0.0, (
        f"Phase 1 rebuffer_ratio should be 0.0, got {result.rebuffer_ratio}"
    )
    print("✓ rebuffer_ratio == 0.0 (Phase 1 — segment-fetch mode)")


def test_measure_streaming_unreachable_returns_failure(qoe: QoEClient) -> None:
    """measure_streaming() to an unreachable URL returns success=False."""
    result = qoe.measure_streaming("http://192.0.2.1/live/stream.m3u8")
    assert result.success is False, (
        "Expected success=False for unreachable streaming URL"
    )
    print("✓ measure_streaming unreachable URL → success=False")


# ---------------------------------------------------------------------------
# Tests: measure_conferencing
# ---------------------------------------------------------------------------


def test_measure_conferencing_returns_qoe_result(qoe: QoEClient) -> None:
    """measure_conferencing() returns a QoEResult instance (may be success=False if no server)."""
    result = qoe.measure_conferencing(_CONF_SESSION_URL, duration_s=5)
    _assert_result_type(result, "measure_conferencing")
    print(f"✓ measure_conferencing returned QoEResult: {result}")


def test_measure_conferencing_success_fields(qoe: QoEClient) -> None:
    """On conferencing success, all stat fields and mos_score are populated."""
    result = qoe.measure_conferencing(_CONF_SESSION_URL, duration_s=10)
    if not result.success:
        pytest.skip(
            f"conf-server may not be running at {_CONF_SESSION_URL!r} — skip"
        )
    assert result.latency_ms is not None, "latency_ms is None"
    assert result.jitter_ms is not None, "jitter_ms is None"
    assert result.packet_loss_pct is not None, "packet_loss_pct is None"
    assert result.mos_score is not None, "mos_score is None"
    assert 1.0 <= result.mos_score <= 4.5, (
        f"mos_score out of range [1.0, 4.5]: {result.mos_score}"
    )
    print(
        f"✓ conferencing: latency={result.latency_ms:.1f}ms, "
        f"jitter={result.jitter_ms:.1f}ms, loss={result.packet_loss_pct:.2f}%, "
        f"MOS={result.mos_score:.3f}"
    )


def test_measure_conferencing_unreachable_returns_failure(qoe: QoEClient) -> None:
    """measure_conferencing() to an unreachable server returns success=False."""
    result = qoe.measure_conferencing("ws://192.0.2.1:8080/session", duration_s=5)
    assert result.success is False, (
        "Expected success=False for unreachable WebRTC session"
    )
    print("✓ measure_conferencing unreachable URL → success=False")


# ---------------------------------------------------------------------------
# Tests: attempt_outbound_connection
# ---------------------------------------------------------------------------


def test_attempt_outbound_connection_allowed(qoe: QoEClient) -> None:
    """attempt_outbound_connection() to an open port returns True."""
    connected = qoe.attempt_outbound_connection(_ALLOWED_HOST, _ALLOWED_PORT)
    assert connected is True, (
        f"Expected TCP connection to {_ALLOWED_HOST}:{_ALLOWED_PORT} to succeed "
        "(ensure productivity-server is running and DUT allows port 80)"
    )
    print(f"✓ TCP {_ALLOWED_HOST}:{_ALLOWED_PORT} → connected=True")


def test_attempt_outbound_connection_unreachable(qoe: QoEClient) -> None:
    """attempt_outbound_connection() to an unreachable host returns False."""
    connected = qoe.attempt_outbound_connection("192.0.2.1", 80, timeout_s=3.0)
    assert connected is False, (
        "Expected connection to 192.0.2.1:80 (RFC 5737 TEST-NET) to fail"
    )
    print("✓ TCP 192.0.2.1:80 → connected=False (unreachable, as expected)")


def test_attempt_outbound_connection_returns_bool(qoe: QoEClient) -> None:
    """attempt_outbound_connection() always returns a bool (not None or string)."""
    result = qoe.attempt_outbound_connection(_ALLOWED_HOST, _ALLOWED_PORT)
    assert isinstance(result, bool), (
        f"Expected bool, got {type(result)}: {result!r}"
    )
    print(f"✓ attempt_outbound_connection returned bool: {result}")
