"""Unit tests for background step definitions.

Tests cover:
- cpe_is_online_and_provisioned (read-only baseline capture)
- user_sets_cpe_gui_password (yield-based teardown)
- discover_admin_user_index (helper)

Mocks: MockACS, MockCPE, MockContext.
Patches: use_case modules at the step's import site
  (tests.step_defs.background_steps.*).
"""

from __future__ import annotations

import inspect
from unittest.mock import MagicMock, patch

import pytest

from tests.unit.mocks import MockACS, MockCPE, MockContext
from tests.step_defs.background_steps import (
    _INDEX_MULTIPLIER,
    _MAX_USER_INDEX,
    _extract_index_from_key,
    cpe_is_online_and_provisioned,
    discover_admin_user_index,
    user_sets_cpe_gui_password,
)

_BG = "tests.step_defs.background_steps"


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
# _extract_index_from_key (helper)
# -----------------------------------------------------------


class TestExtractIndexFromKey:

    def test_extracts_from_normal_key(self):
        key = "Device.Users.User.10.Username"
        assert _extract_index_from_key(key) == 10

    def test_extracts_from_mangled_key(self):
        key = "Device.Users.User.10.Usernam"
        assert _extract_index_from_key(key) == 10

    def test_returns_none_for_short_key(self):
        assert _extract_index_from_key("Device.Users") is None

    def test_returns_none_for_non_numeric_index(self):
        key = "Device.Users.User.abc.Username"
        assert _extract_index_from_key(key) is None


# -----------------------------------------------------------
# discover_admin_user_index (per-index GPV scan)
# -----------------------------------------------------------


class TestDiscoverAdminUserIndex:
    """Tests for discover_admin_user_index.

    Patches acs_use_cases.get_parameter_value which is called
    once for UserNumberOfEntries, then once per candidate index
    for the Username scan.
    """

    @patch(f"{_BG}.acs_use_cases")
    def test_finds_admin_at_index_10(self, mock_uc, acs, cpe):
        def _gpv(acs, cpe, param, **kw):
            if "UserNumberOfEntries" in param:
                return "11"
            if "User.10.Username" in param:
                return "admin"
            raise Exception("not found")
        mock_uc.get_parameter_value.side_effect = _gpv
        assert discover_admin_user_index(acs, cpe) == 10

    @patch(f"{_BG}.acs_use_cases")
    def test_finds_admin_among_multiple_users(
        self, mock_uc, acs, cpe,
    ):
        def _gpv(acs, cpe, param, **kw):
            if "UserNumberOfEntries" in param:
                return "3"
            if "User.5.Username" in param:
                return "guest"
            if "User.11.Username" in param:
                return "admin"
            raise Exception("not found")
        mock_uc.get_parameter_value.side_effect = _gpv
        assert discover_admin_user_index(acs, cpe) == 11

    @patch(f"{_BG}.acs_use_cases")
    def test_handles_non_contiguous_indices(
        self, mock_uc, acs, cpe,
    ):
        def _gpv(acs, cpe, param, **kw):
            if "UserNumberOfEntries" in param:
                return "11"
            if "User.1.Username" in param:
                return "operator"
            if "User.50.Username" in param:
                return "admin"
            raise Exception("not found")
        mock_uc.get_parameter_value.side_effect = _gpv
        assert discover_admin_user_index(acs, cpe) == 50

    @patch(f"{_BG}.acs_use_cases")
    def test_raises_when_no_admin(self, mock_uc, acs, cpe):
        def _gpv(acs, cpe, param, **kw):
            if "UserNumberOfEntries" in param:
                return "2"
            if "User.1.Username" in param:
                return "guest"
            raise Exception("not found")
        mock_uc.get_parameter_value.side_effect = _gpv
        with pytest.raises(
            AssertionError, match="No user with username='admin'"
        ):
            discover_admin_user_index(acs, cpe)

    @patch(f"{_BG}.acs_use_cases")
    def test_raises_when_all_indices_fail(
        self, mock_uc, acs, cpe,
    ):
        def _gpv(acs, cpe, param, **kw):
            if "UserNumberOfEntries" in param:
                return "2"
            raise Exception("not found")
        mock_uc.get_parameter_value.side_effect = _gpv
        with pytest.raises(
            AssertionError, match="No user with username='admin'"
        ):
            discover_admin_user_index(acs, cpe)

    @patch(f"{_BG}.acs_use_cases")
    def test_falls_back_to_fixed_ceiling_when_count_unavailable(
        self, mock_uc, acs, cpe,
    ):
        """When UserNumberOfEntries fails, scans up to _MAX_USER_INDEX."""
        call_count = {"n": 0}

        def _gpv(acs, cpe, param, **kw):
            call_count["n"] += 1
            if "UserNumberOfEntries" in param:
                raise Exception("GPV returned empty/malformed")
            if "User.10.Username" in param:
                return "admin"
            raise Exception("not found")
        mock_uc.get_parameter_value.side_effect = _gpv
        assert discover_admin_user_index(acs, cpe) == 10

    @patch(f"{_BG}.acs_use_cases")
    def test_range_scales_with_user_count(
        self, mock_uc, acs, cpe,
    ):
        """Scan range = user_count * _INDEX_MULTIPLIER."""
        highest_queried = {"idx": 0}

        def _gpv(acs, cpe, param, **kw):
            if "UserNumberOfEntries" in param:
                return "4"
            for i in range(1, 100):
                if f"User.{i}.Username" in param:
                    highest_queried["idx"] = max(
                        highest_queried["idx"], i,
                    )
                    break
            if "User.20.Username" in param:
                return "admin"
            raise Exception("not found")
        mock_uc.get_parameter_value.side_effect = _gpv
        discover_admin_user_index(acs, cpe)
        assert highest_queried["idx"] == 20  # stopped at admin

    @patch(f"{_BG}.acs_use_cases")
    def test_skips_empty_usernames(self, mock_uc, acs, cpe):
        def _gpv(acs, cpe, param, **kw):
            if "UserNumberOfEntries" in param:
                return "3"
            if "User.1.Username" in param:
                return "  "
            if "User.2.Username" in param:
                return "admin"
            raise Exception("not found")
        mock_uc.get_parameter_value.side_effect = _gpv
        assert discover_admin_user_index(acs, cpe) == 2


# -----------------------------------------------------------
# cpe_is_online_and_provisioned (read-only, no yield)
# -----------------------------------------------------------


class TestCpeIsOnlineAndProvisioned:

    @patch(f"{_BG}.cpe_use_cases")
    @patch(f"{_BG}.acs_use_cases")
    def test_captures_baseline(
        self, mock_acs_uc, mock_cpe_uc,
        acs, cpe, bf_context,
    ):
        mock_acs_uc.get_parameter_value.return_value = "1.0.0"
        mock_cpe_uc.get_console_uptime_seconds.return_value = 120

        cpe_is_online_and_provisioned(acs, cpe, bf_context)

        fw = bf_context.config_before_reboot["firmware_version"]
        assert fw["value"] == "1.0.0"
        assert bf_context.initial_uptime == 120


# -----------------------------------------------------------
# user_sets_cpe_gui_password (yield-based teardown)
# -----------------------------------------------------------

_PWD_PARAM = "Device.Users.User.10.Password"


class TestUserSetsCpeGuiPassword:

    @patch(f"{_BG}.time")
    @patch(f"{_BG}.acs_use_cases")
    def test_sets_password_successfully(
        self, mock_acs_uc, _mock_time,
        acs, cpe, bf_context,
    ):
        bf_context.admin_user_index = 10
        mock_acs_uc.get_parameter_value.return_value = "hash"
        mock_acs_uc.set_parameter_value.return_value = True

        gen = _run_step(
            user_sets_cpe_gui_password,
            acs, cpe, bf_context, "p@ss!",
        )

        assert gen is not None
        mock_acs_uc.set_parameter_value.assert_any_call(
            acs, cpe, _PWD_PARAM, "p@ss!",
        )

    @patch(f"{_BG}.time")
    @patch(f"{_BG}.acs_use_cases")
    def test_raises_on_spv_failure(
        self, mock_acs_uc, _mock_time,
        acs, cpe, bf_context,
    ):
        bf_context.admin_user_index = 10
        mock_acs_uc.get_parameter_value.return_value = "old"
        mock_acs_uc.set_parameter_value.return_value = False

        with pytest.raises(
            AssertionError, match="Failed to set CPE GUI"
        ):
            _run_step(
                user_sets_cpe_gui_password,
                acs, cpe, bf_context, "p@ss!",
            )

    @patch(f"{_BG}.time")
    @patch(f"{_BG}.acs_use_cases")
    def test_stores_config_before_reboot(
        self, mock_acs_uc, _mock_time,
        acs, cpe, bf_context,
    ):
        bf_context.admin_user_index = 10
        mock_acs_uc.get_parameter_value.return_value = "enc"
        mock_acs_uc.set_parameter_value.return_value = True

        _run_step(
            user_sets_cpe_gui_password,
            acs, cpe, bf_context, "secret",
        )

        items = bf_context.config_before_reboot["users"]["items"]
        assert "10" in items
        assert items["10"]["Password"]["gpv_param"] == _PWD_PARAM

    @patch(
        f"{_BG}.discover_admin_user_index",
        return_value=5,
    )
    @patch(f"{_BG}.time")
    @patch(f"{_BG}.acs_use_cases")
    def test_discovers_admin_index_when_not_cached(
        self, mock_acs_uc, _mock_time, mock_discover,
        acs, cpe, bf_context,
    ):
        mock_acs_uc.get_parameter_value.return_value = "h"
        mock_acs_uc.set_parameter_value.return_value = True

        _run_step(
            user_sets_cpe_gui_password,
            acs, cpe, bf_context, "pass",
        )

        mock_discover.assert_called_once_with(acs, cpe)
        assert bf_context.admin_user_index == 5


class TestPasswordYieldTeardown:
    """Verify yield-based teardown of user_sets_cpe_gui_password."""

    @patch(f"{_BG}.time")
    @patch(f"{_BG}.acs_use_cases")
    def test_teardown_restores_password(
        self, mock_acs_uc, _mock_time,
        acs, cpe, bf_context,
    ):
        bf_context.admin_user_index = 10
        mock_acs_uc.get_parameter_value.return_value = "h"
        mock_acs_uc.set_parameter_value.return_value = True

        gen = _run_step(
            user_sets_cpe_gui_password,
            acs, cpe, bf_context, "new",
        )
        mock_acs_uc.set_parameter_value.reset_mock()

        with pytest.raises(StopIteration):
            next(gen)

        mock_acs_uc.set_parameter_value.assert_called_once_with(
            acs, cpe, _PWD_PARAM, "admin",
        )

    @patch(f"{_BG}.time")
    @patch(f"{_BG}.acs_use_cases")
    def test_teardown_swallows_exception(
        self, mock_acs_uc, _mock_time,
        acs, cpe, bf_context,
    ):
        bf_context.admin_user_index = 10
        mock_acs_uc.get_parameter_value.return_value = "h"
        mock_acs_uc.set_parameter_value.return_value = True

        gen = _run_step(
            user_sets_cpe_gui_password,
            acs, cpe, bf_context, "new",
        )
        mock_acs_uc.set_parameter_value.side_effect = (
            RuntimeError("ACS unreachable")
        )

        with pytest.raises(StopIteration):
            next(gen)

    @patch(f"{_BG}.time")
    @patch(f"{_BG}.acs_use_cases")
    def test_teardown_is_idempotent(
        self, mock_acs_uc, _mock_time,
        acs, cpe, bf_context,
    ):
        """Succeeds even if password was already restored."""
        bf_context.admin_user_index = 10
        mock_acs_uc.get_parameter_value.return_value = "h"
        mock_acs_uc.set_parameter_value.return_value = True

        gen = _run_step(
            user_sets_cpe_gui_password,
            acs, cpe, bf_context, "new",
        )
        mock_acs_uc.set_parameter_value.side_effect = (
            Exception("already default")
        )

        with pytest.raises(StopIteration):
            next(gen)
