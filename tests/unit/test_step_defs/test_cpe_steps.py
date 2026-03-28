"""Unit tests for CPE step definitions.

Tests cover:
- cpe_is_unreachable_for_tr069 (yield-based teardown)
- cpe_does_not_reboot (verification step, no yield)

Mocks: MockACS, MockCPE, MockContext.
Patches: use_case modules at the step's import site
  (tests.step_defs.cpe_steps.*).
"""

from __future__ import annotations

import inspect
from unittest.mock import patch

import pytest

from tests.unit.mocks import MockACS, MockCPE, MockContext
from tests.step_defs.cpe_steps import (
    cpe_does_not_reboot,
    cpe_is_unreachable_for_tr069,
)

_CPE = "tests.step_defs.cpe_steps"


def _run_step(step_fn, *args, **kwargs):
    """Execute the setup portion of a step function.

    Yielding steps are advanced to the first yield so
    the setup code runs.  Non-yielding steps are called
    normally.  The generator (or None) is returned so
    tests can optionally verify teardown.
    """
    result = step_fn(*args, **kwargs)
    if inspect.isgenerator(result):
        next(result)
        return result
    return result


# -----------------------------------------------------------
# Fixtures
# -----------------------------------------------------------


@pytest.fixture
def acs() -> MockACS:
    return MockACS()


@pytest.fixture
def cpe() -> MockCPE:
    return MockCPE()


@pytest.fixture
def bf_context() -> MockContext:
    return MockContext()


# -----------------------------------------------------------
# cpe_is_unreachable_for_tr069 (yield-based teardown)
# -----------------------------------------------------------


class TestCpeIsUnreachableForTr069:

    @patch(f"{_CPE}.cpe_use_cases")
    def test_stops_tr069_client(
        self, mock_cpe_uc, acs, cpe, bf_context,
    ):
        gen = _run_step(
            cpe_is_unreachable_for_tr069,
            acs, cpe, bf_context,
        )
        assert gen is not None
        mock_cpe_uc.stop_tr069_client.assert_called_once_with(
            cpe,
        )

    @patch(f"{_CPE}.cpe_use_cases")
    def test_sets_context_attributes(
        self, _mock_cpe_uc, acs, cpe, bf_context,
    ):
        _run_step(
            cpe_is_unreachable_for_tr069,
            acs, cpe, bf_context,
        )
        assert bf_context.reboot_cpe_id == "mock_cpe_001"
        assert bf_context.cpe_was_taken_offline is True
        assert bf_context.test_start_timestamp is not None
        assert bf_context.cpe_offline_timestamp is not None


class TestCpeTr069YieldTeardown:
    """Verify yield-based teardown of cpe_is_unreachable_for_tr069."""

    @patch(f"{_CPE}.cpe_use_cases")
    def test_teardown_restarts_tr069_client(
        self, mock_cpe_uc, acs, cpe, bf_context,
    ):
        gen = _run_step(
            cpe_is_unreachable_for_tr069,
            acs, cpe, bf_context,
        )
        mock_cpe_uc.start_tr069_client.reset_mock()

        with pytest.raises(StopIteration):
            next(gen)

        mock_cpe_uc.start_tr069_client.assert_called_once_with(
            cpe,
        )

    @patch(f"{_CPE}.cpe_use_cases")
    def test_teardown_swallows_exception(
        self, mock_cpe_uc, acs, cpe, bf_context,
    ):
        gen = _run_step(
            cpe_is_unreachable_for_tr069,
            acs, cpe, bf_context,
        )
        mock_cpe_uc.start_tr069_client.side_effect = (
            RuntimeError("CPE unreachable")
        )

        with pytest.raises(StopIteration):
            next(gen)

    @patch(f"{_CPE}.cpe_use_cases")
    def test_teardown_is_idempotent(
        self, mock_cpe_uc, acs, cpe, bf_context,
    ):
        """Succeeds even if TR-069 was already restarted."""
        gen = _run_step(
            cpe_is_unreachable_for_tr069,
            acs, cpe, bf_context,
        )
        mock_cpe_uc.start_tr069_client.side_effect = (
            Exception("already running")
        )

        with pytest.raises(StopIteration):
            next(gen)


# -----------------------------------------------------------
# cpe_does_not_reboot (verification step, no yield)
# -----------------------------------------------------------


class TestCpeDoesNotReboot:

    @patch(f"{_CPE}.cpe_use_cases")
    def test_passes_when_uptime_increases(
        self, mock_cpe_uc, acs, cpe, bf_context,
    ):
        bf_context.initial_uptime = 100
        mock_cpe_uc.get_console_uptime_seconds.return_value = 200
        cpe_does_not_reboot(acs, cpe, bf_context)

    @patch(f"{_CPE}.cpe_use_cases")
    def test_fails_when_uptime_decreased(
        self, mock_cpe_uc, acs, cpe, bf_context,
    ):
        bf_context.initial_uptime = 100
        mock_cpe_uc.get_console_uptime_seconds.return_value = 10

        with pytest.raises(
            AssertionError, match="appears to have rebooted"
        ):
            cpe_does_not_reboot(acs, cpe, bf_context)
