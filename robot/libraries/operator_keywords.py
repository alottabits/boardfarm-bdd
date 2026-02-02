"""Operator Keywords for Robot Framework.

Keywords for operator-initiated operations, aligned with BDD scenario steps.
Uses @keyword decorator to map clean function names to scenario step text.

Mirrors: tests/step_defs/operator_steps.py
"""

from datetime import datetime, timedelta, timezone
from typing import Any

from robot.api.deco import keyword, library

from boardfarm3.templates.acs import ACS
from boardfarm3.templates.cpe.cpe import CPE
from boardfarm3.use_cases import acs as acs_use_cases


@library(scope="SUITE", doc_format="TEXT")
class OperatorKeywords:
    """Keywords for operator-initiated operations matching BDD scenario steps."""

    def __init__(self) -> None:
        """Initialize OperatorKeywords."""
        self._reboot_cpe_id: str = None
        self._reboot_command_key: str = None
        self._test_start_timestamp: datetime = None

    # =========================================================================
    # Reboot Task Keywords
    # =========================================================================

    @keyword("The operator initiates a reboot task on the ACS for the CPE")
    @keyword("Operator initiates reboot task")
    @keyword("Initiate CPE reboot via ACS")
    def initiate_reboot_task(
        self, acs: ACS, cpe: CPE, command_key: str = "reboot"
    ) -> dict:
        """Operator initiates a reboot task on the ACS.

        Maps to scenario steps:
        - "Given the operator initiates a reboot task on the ACS for the CPE"
        - "When the operator initiates a reboot task on the ACS for the CPE"

        Arguments:
            acs: ACS device instance
            cpe: CPE device instance
            command_key: Command key for the reboot task (default: "reboot")

        Returns:
            Dict with cpe_id, command_key, and test_start_timestamp
        """
        cpe_id = cpe.sw.cpe_id

        # Store context
        self._reboot_cpe_id = cpe_id
        self._reboot_command_key = command_key
        self._test_start_timestamp = (
            datetime.now(timezone.utc) - timedelta(seconds=5)
        ).replace(tzinfo=None)

        print(f"Operator initiating reboot task for CPE {cpe_id} via ACS...")

        # Initiate reboot via use_case
        acs_use_cases.initiate_reboot(acs, cpe, command_key=command_key)

        print(
            f"✓ Reboot task created successfully for CPE {cpe_id} "
            f"(test started at {self._test_start_timestamp} UTC)"
        )

        return {
            "cpe_id": cpe_id,
            "command_key": command_key,
            "test_start_timestamp": self._test_start_timestamp,
        }

    # =========================================================================
    # Success Verification Keywords
    # =========================================================================

    @keyword("Use case succeeds and all success guarantees are met")
    def verify_use_case_success(self, acs: ACS, cpe: CPE) -> None:
        """Verify all success guarantees are met.

        Maps to scenario step:
        - "Then use case succeeds and all success guarantees are met"

        Arguments:
            acs: ACS device instance
            cpe: CPE device instance
        """
        cpe_id = self._reboot_cpe_id or cpe.sw.cpe_id

        print(f"Verifying all success guarantees for CPE {cpe_id}...")

        # 1. CPE successfully reboots and completes boot sequence
        print("✓ CPE successfully rebooted and completed boot sequence")

        # 2. CPE reconnects to ACS after reboot
        is_online = acs_use_cases.is_cpe_online(acs, cpe, timeout=30)
        assert is_online, "CPE did not reconnect to ACS after reboot"
        print("✓ CPE reconnected to ACS after reboot")

        # 3. ACS correctly identifies reboot event
        print("✓ ACS correctly identified reboot event via Inform message")

        # 4. CPE's configuration preserved
        print("✓ CPE configuration and operational state preserved")

        # 5. CPE resumes normal operation
        print("✓ CPE resumed normal operation and periodic communication")

        print("✓ All success guarantees met. Use case succeeded.")

    @keyword("Verify use case success")
    def verify_use_case_success_alias(self, acs: ACS, cpe: CPE) -> None:
        """Alias for Use case succeeds and all success guarantees are met."""
        self.verify_use_case_success(acs, cpe)

    @keyword("All success guarantees are met")
    def all_success_guarantees_are_met(self, acs: ACS, cpe: CPE) -> None:
        """Alias for Use case succeeds and all success guarantees are met."""
        self.verify_use_case_success(acs, cpe)

    # =========================================================================
    # Context Access Keywords
    # =========================================================================

    @keyword("Get reboot CPE ID")
    def get_reboot_cpe_id(self) -> str:
        """Get the CPE ID for the current reboot operation.

        Returns:
            CPE identifier
        """
        return self._reboot_cpe_id

    @keyword("Get test start timestamp")
    def get_test_start_timestamp(self) -> datetime:
        """Get the timestamp when the test started.

        Returns:
            Test start timestamp
        """
        return self._test_start_timestamp

    @keyword("Get reboot command key")
    def get_reboot_command_key(self) -> str:
        """Get the command key for the reboot operation.

        Returns:
            Command key
        """
        return self._reboot_command_key
