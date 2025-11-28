"""Unit test conftest for step definitions.

This conftest is loaded by pytest when running unit tests from this directory.
It overrides fixtures from the root conftest.py to provide mock objects
instead of real boardfarm devices, enabling isolated unit testing of
step definition functions.
"""

import pytest

from tests.unit.mocks import (
    MockACS,
    MockContext,
    MockCPE,
    MockSIPPhone,
    MockSIPServer,
)


# -- Mock Device Fixtures --
# These fixtures override the real device fixtures in the root conftest.py


@pytest.fixture
def cpe() -> MockCPE:
    """Mock CPE device fixture."""
    return MockCPE()


@pytest.fixture
def acs() -> MockACS:
    """Mock ACS (GenieACS) device fixture."""
    return MockACS()


@pytest.fixture
def lan_phone() -> MockSIPPhone:
    """Mock LAN SIP phone fixture."""
    return MockSIPPhone(name="lan_phone", number="1000")


@pytest.fixture
def wan_phone() -> MockSIPPhone:
    """Mock WAN SIP phone fixture."""
    return MockSIPPhone(name="wan_phone", number="2000")


@pytest.fixture
def wan_phone2() -> MockSIPPhone:
    """Mock second WAN SIP phone fixture."""
    return MockSIPPhone(name="wan_phone2", number="3000")


@pytest.fixture
def sipcenter() -> MockSIPServer:
    """Mock SIP server (Kamailio) fixture."""
    return MockSIPServer()


# -- Mock Context Fixture --


@pytest.fixture
def bf_context() -> MockContext:
    """Mock Boardfarm context (bf_context) fixture.
    
    Provides a clean, isolated context for each unit test.
    """
    return MockContext()


# -- Override and Disable Root Autouse Fixtures --
# The following fixtures override the autouse cleanup fixtures from the root
# conftest.py. By providing empty implementations, we prevent them from
# running during unit tests, where they are not needed and would cause errors.


@pytest.fixture(scope="function", autouse=True)
def cleanup_cpe_config_after_scenario(cpe: MockCPE, bf_context: MockContext):
    """Override and disable the CPE config cleanup fixture for unit tests."""
    yield  # Allows the test to run
    # No cleanup action is performed


@pytest.fixture(scope="function", autouse=True)
def cleanup_sip_phones_after_scenario(bf_context: MockContext):
    """Override and disable the SIP phone cleanup fixture for unit tests."""
    yield  # Allows the test to run
    # No cleanup action is performed
