"""Conftest for Robot keyword unit tests.

Overrides autouse fixtures from tests/conftest.py so robot/utest tests
run without the boardfarm plugin (no device_manager). These tests use
mocks only.
"""

import pytest

from tests.unit.mocks import MockContext


@pytest.fixture(scope="function", autouse=True)
def cleanup_cpe_config_after_scenario():
    """Override: no-op for robot keyword unit tests."""
    yield


@pytest.fixture(scope="function", autouse=True)
def cleanup_sip_phones_after_scenario():
    """Override: no-op for robot keyword unit tests."""
    yield


@pytest.fixture
def bf_context() -> MockContext:
    """Mock context for tests that need it."""
    return MockContext()
