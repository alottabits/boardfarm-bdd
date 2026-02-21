"""Unit test conftest for Robot keyword libraries.

Mirrors tests/unit/test_step_defs/conftest.py structure.
Provides mock device fixtures for isolated unit testing of keywords.
"""

import sys
from pathlib import Path

# Ensure boardfarm-bdd root is on path for tests.unit.mocks
_root = Path(__file__).resolve().parents[3]
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

import pytest

from tests.unit.mocks import (
    MockContext,
    MockSIPPhone,
    MockSIPServer,
)

from .voice_keywords_loader import VoiceKeywords


# -- Mock Device Fixtures --
# Mirrors tests/unit/test_step_defs/conftest.py


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


@pytest.fixture
def bf_context() -> MockContext:
    """Mock Boardfarm context (bf_context) fixture."""
    return MockContext()


@pytest.fixture
def voice_keywords_lib() -> VoiceKeywords:
    """VoiceKeywords library instance for testing."""
    return VoiceKeywords()
