"""Conftest for bf_use_cases tests.

Provides:
- No-op overrides for the root conftest.py autouse fixtures so that *unit* tests
  in this directory can run without the boardfarm plugin (no --board-name required).
- ``wan1_tc``, ``wan2_tc``, and ``tc`` device fixtures for *integration* tests.

Unit tests use ``unittest.mock`` exclusively and never request these device
fixtures, so the boardfarm ``devices`` dependency is never triggered.
Integration tests request ``devices`` and/or ``boardfarm_config`` directly
through their function signatures.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from boardfarm3.templates.qoe_client import QoEClient
    from boardfarm3.templates.traffic_controller import TrafficController
    from boardfarm3.templates.wan_edge import WANEdgeDevice


# ---------------------------------------------------------------------------
# Override root autouse fixtures
# The root tests/conftest.py autouse fixtures depend on boardfarm device
# fixtures (devices, acs, cpe, ...) that are unavailable in pure unit tests.
# Override them here with benign no-ops.
# ---------------------------------------------------------------------------


@pytest.fixture(scope="function", autouse=True)
def cleanup_cpe_config_after_scenario() -> None:  # type: ignore[override]
    """No-op CPE cleanup — no CPE in SD-WAN / use-case-test scope."""
    yield


@pytest.fixture(scope="function", autouse=True)
def cleanup_sip_phones_after_scenario() -> None:  # type: ignore[override]
    """No-op SIP phone cleanup — no SIP phones in SD-WAN / use-case-test scope."""
    yield


# ---------------------------------------------------------------------------
# Traffic controller device fixtures (integration tests only)
# Unit tests never request these, so the boardfarm ``devices`` dependency
# is never triggered when running without --board-name.
# ---------------------------------------------------------------------------


@pytest.fixture()
def wan1_tc(devices: object) -> TrafficController:
    """wan1_tc traffic controller device (integration tests only)."""
    dev = getattr(devices, "wan1_tc", None)
    if dev is None:
        pytest.skip("wan1_tc not in testbed (use --board-name sdwan)")
    return dev  # type: ignore[return-value]


@pytest.fixture()
def wan2_tc(devices: object) -> TrafficController:
    """wan2_tc traffic controller device (integration tests only)."""
    dev = getattr(devices, "wan2_tc", None)
    if dev is None:
        pytest.skip("wan2_tc not in testbed (use --board-name sdwan)")
    return dev  # type: ignore[return-value]


@pytest.fixture()
def tc(wan1_tc: TrafficController) -> TrafficController:
    """Default TC device for integration tests (wan1_tc); clears impairment after each test."""
    yield wan1_tc
    try:
        wan1_tc.clear()
    except Exception:  # noqa: BLE001
        pass


@pytest.fixture()
def lan_client(devices: object) -> "QoEClient":
    """lan_client QoEClient device (integration tests only)."""
    dev = getattr(devices, "lan_client", None)
    if dev is None:
        pytest.skip("lan_client not in testbed (use --board-name sdwan)")
    return dev  # type: ignore[return-value]


@pytest.fixture()
def sdwan(devices: object) -> "WANEdgeDevice":
    """sdwan WANEdgeDevice (integration tests only)."""
    dev = getattr(devices, "sdwan", None)
    if dev is None:
        pytest.skip("sdwan not in testbed (use --board-name sdwan)")
    return dev  # type: ignore[return-value]
