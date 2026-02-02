"""CPE Keywords for Robot Framework.

Keywords for CPE (Customer Premises Equipment) operations, aligned with BDD scenario steps.
Uses @keyword decorator to map clean function names to scenario step text.

Mirrors: tests/step_defs/cpe_steps.py
"""

from datetime import datetime, timedelta, timezone
from typing import Any

from robot.api.deco import keyword, library

from boardfarm3.templates.acs import ACS
from boardfarm3.templates.cpe.cpe import CPE
from boardfarm3.use_cases import acs as acs_use_cases
from boardfarm3.use_cases import cpe as cpe_use_cases


@library(scope="SUITE", doc_format="TEXT")
class CpeKeywords:
    """Keywords for CPE operations matching BDD scenario steps."""

    def __init__(self) -> None:
        """Initialize CpeKeywords."""
        self._context: dict[str, Any] = {}

    # =========================================================================
    # Connection and Session Keywords
    # =========================================================================

    @keyword("The CPE receives the connection request and initiates a session")
    def receive_connection_request_initiate_session(
        self, acs: ACS, cpe: CPE, cpe_id: str = None
    ) -> None:
        """CPE receives connection request and initiates session.

        Maps to scenario step:
        - "When the CPE receives the connection request and initiates a session"

        Arguments:
            acs: ACS device instance
            cpe: CPE device instance
            cpe_id: CPE identifier (optional)
        """
        if cpe_id is None:
            cpe_id = cpe.sw.cpe_id

        print(
            f"Waiting for CPE {cpe_id} to receive connection request "
            "and initiate session..."
        )

    @keyword("CPE initiates session with ACS")
    def cpe_initiates_session_with_acs(
        self, acs: ACS, cpe: CPE, cpe_id: str = None
    ) -> None:
        """Alias for The CPE receives the connection request and initiates a session."""
        self.receive_connection_request_initiate_session(acs, cpe, cpe_id)

    @keyword("The CPE sends an Inform message to the ACS")
    def send_inform_message(
        self, acs: ACS, cpe: CPE, cpe_id: str = None, since: Any = None, timeout: int = 120
    ) -> None:
        """CPE sends an Inform message to the ACS.

        Maps to scenario steps:
        - "When the CPE sends an Inform message to the ACS"
        - "Then the CPE sends an Inform message to the ACS"

        Arguments:
            acs: ACS device instance
            cpe: CPE device instance
            cpe_id: CPE identifier (optional)
            since: Timestamp to filter logs from (optional)
            timeout: Timeout in seconds (default: 120, matching step_defs)
        """
        if cpe_id is None:
            cpe_id = cpe.sw.cpe_id

        print(f"Waiting for CPE {cpe_id} to send Inform message (timeout={timeout}s)...")

        acs_use_cases.wait_for_inform_message(acs, cpe_id, since=since, timeout=timeout)

        print(f"✓ CPE {cpe_id} sent Inform message (verified in GenieACS logs)")

    @keyword("CPE sends Inform message")
    def cpe_sends_inform_message(
        self, acs: ACS, cpe: CPE, cpe_id: str = None, since: Any = None, timeout: int = 120
    ) -> None:
        """Alias for The CPE sends an Inform message to the ACS."""
        self.send_inform_message(acs, cpe, cpe_id, since, timeout)

    # =========================================================================
    # Reboot Keywords
    # =========================================================================

    @keyword("The CPE executes the reboot command and restarts")
    def execute_reboot_and_restart(self, cpe: CPE, timeout: int = 60) -> None:
        """CPE executes the reboot command and restarts.

        Maps to scenario step:
        - "Then the CPE executes the reboot command and restarts"

        Arguments:
            cpe: CPE device instance
            timeout: Timeout in seconds (default: 60)
        """
        cpe_id = cpe.sw.cpe_id

        print(f"Verifying CPE {cpe_id} executes reboot and restarts...")

        cpe_use_cases.wait_for_reboot_completion(cpe, timeout=timeout)

        print(f"✓ CPE {cpe_id} reboot completed")

    @keyword("CPE executes reboot")
    def cpe_executes_reboot(self, cpe: CPE, timeout: int = 60) -> None:
        """Alias for The CPE executes the reboot command and restarts."""
        self.execute_reboot_and_restart(cpe, timeout)

    @keyword("The CPE sends an Inform message after boot completion")
    def send_inform_after_boot(
        self, acs: ACS, cpe: CPE, cpe_id: str = None, since: Any = None, timeout: int = 240
    ) -> str:
        """CPE sends Inform after boot completion.

        Maps to scenario step:
        - "Then after completing the boot sequence, the CPE sends an Inform message"

        Arguments:
            acs: ACS device instance
            cpe: CPE device instance
            cpe_id: CPE identifier (optional)
            since: Timestamp to filter logs from (optional)
            timeout: Timeout in seconds (default: 240)

        Returns:
            Inform timestamp
        """
        if cpe_id is None:
            cpe_id = cpe.sw.cpe_id

        print(
            f"Waiting for CPE {cpe_id} to complete boot and send "
            "post-reboot Inform message..."
        )

        inform_timestamp = acs_use_cases.wait_for_boot_inform(
            acs, cpe_id, since=since, timeout=timeout
        )

        print(
            f"✓ CPE {cpe_id} sent post-reboot Inform message at {inform_timestamp} UTC"
        )

        # Refresh console connection after reboot
        print("↻ Refreshing CPE console connection after reboot...")
        if cpe_use_cases.refresh_console_connection(cpe):
            print("✓ Console connection refreshed successfully")
        else:
            print("⚠ Could not refresh console connection")

        return str(inform_timestamp)

    @keyword("CPE sends boot Inform")
    def cpe_sends_boot_inform(
        self, acs: ACS, cpe: CPE, cpe_id: str = None, since: Any = None, timeout: int = 240
    ) -> str:
        """Alias for The CPE sends an Inform message after boot completion."""
        return self.send_inform_after_boot(acs, cpe, cpe_id, since, timeout)

    @keyword("The CPE does not reboot")
    def verify_no_reboot(self, cpe: CPE, initial_uptime: float) -> None:
        """Verify the CPE does not reboot.

        Maps to scenario step:
        - "Then the CPE does not reboot"

        Arguments:
            cpe: CPE device instance
            initial_uptime: Initial uptime in seconds (before test)
        """
        import time
        time.sleep(5)

        current_uptime = cpe_use_cases.get_console_uptime_seconds(cpe)

        assert initial_uptime, "Initial uptime was not set"
        assert current_uptime > initial_uptime, (
            f"CPE appears to have rebooted. "
            f"Initial uptime: {initial_uptime}, "
            f"Current uptime: {current_uptime}"
        )

        print(
            f"✓ Verified that CPE did not reboot. "
            f"Uptime increased from {initial_uptime} to {current_uptime}."
        )

    @keyword("Verify CPE did not reboot")
    def verify_cpe_did_not_reboot(self, cpe: CPE, initial_uptime: float) -> None:
        """Alias for The CPE does not reboot."""
        self.verify_no_reboot(cpe, initial_uptime)

    # =========================================================================
    # Normal Operation Keywords
    # =========================================================================

    @keyword("The CPE resumes normal operation")
    def verify_normal_operation(
        self, acs: ACS, cpe: CPE, cpe_id: str = None, timeout: int = 60
    ) -> None:
        """CPE resumes normal operation.

        Maps to scenario step:
        - "Then the CPE resumes normal operation, continuing periodic communication"

        Arguments:
            acs: ACS device instance
            cpe: CPE device instance
            cpe_id: CPE identifier (optional)
            timeout: Timeout in seconds (default: 60, increased for post-reboot)
        """
        if cpe_id is None:
            cpe_id = cpe.sw.cpe_id

        print(f"Verifying CPE {cpe_id} has resumed normal operation (timeout={timeout}s)...")

        is_online = acs_use_cases.is_cpe_online(acs, cpe, timeout=timeout)

        assert is_online, (
            f"CPE {cpe_id} is not responding, "
            "indicating it has not resumed normal operation"
        )

        print(
            f"✓ CPE {cpe_id} has resumed normal operation "
            "and periodic communication"
        )

    @keyword("CPE resumes normal operation")
    def cpe_resumes_normal_operation(
        self, acs: ACS, cpe: CPE, cpe_id: str = None, timeout: int = 60
    ) -> None:
        """Alias for The CPE resumes normal operation."""
        self.verify_normal_operation(acs, cpe, cpe_id, timeout)

    @keyword("The CPE configuration is preserved after reboot")
    def verify_config_preserved(
        self, acs: ACS, cpe: CPE, config_before: dict = None, cpe_id: str = None, timeout: int = 30
    ) -> None:
        """CPE configuration preserved after reboot.

        Maps to scenario step:
        - "Then the CPE's configuration and operational state are preserved"

        Arguments:
            acs: ACS device instance
            cpe: CPE device instance
            config_before: Configuration captured before reboot (optional)
            cpe_id: CPE identifier (optional)
            timeout: Timeout in seconds (default: 30)
        """
        if cpe_id is None:
            cpe_id = cpe.sw.cpe_id

        print(f"Verifying configuration preservation for CPE {cpe_id}...")

        if not config_before:
            print(
                "⚠ Configuration was not captured before reboot. "
                "Skipping detailed verification."
            )
            is_online = acs_use_cases.is_cpe_online(acs, cpe, timeout=timeout)
            assert is_online, f"CPE {cpe_id} is not responding"
            print(f"✓ CPE {cpe_id} is online (basic verification)")
            return

        verification_errors = cpe_use_cases.verify_config_preservation(
            cpe, acs, config_before
        )

        if verification_errors:
            error_msg = (
                "Configuration was not fully preserved after reboot:\n"
                + "\n".join(f"  - {error}" for error in verification_errors)
            )
            raise AssertionError(error_msg)

        print("✓ All configuration parameters preserved after reboot")

    @keyword("Verify CPE configuration preserved")
    def verify_cpe_configuration_preserved(
        self, acs: ACS, cpe: CPE, config_before: dict = None, cpe_id: str = None, timeout: int = 30
    ) -> None:
        """Alias for The CPE configuration is preserved after reboot."""
        self.verify_config_preserved(acs, cpe, config_before, cpe_id, timeout)

    # =========================================================================
    # TR-069 Agent Keywords
    # =========================================================================

    @keyword("The CPE is unreachable for TR-069 sessions")
    def make_unreachable_for_tr069(self, cpe: CPE) -> dict:
        """Make CPE unreachable for TR-069 sessions.

        Maps to scenario step:
        - "Given the CPE is unreachable for TR-069 sessions"

        Arguments:
            cpe: CPE device instance

        Returns:
            Context dict with cpe_id and timestamps
        """
        cpe_id = cpe.sw.cpe_id

        context = {
            "cpe_id": cpe_id,
            "test_start_timestamp": (
                datetime.now(timezone.utc) - timedelta(seconds=5)
            ).replace(tzinfo=None),
        }

        print(f"Making CPE {cpe_id} unreachable for TR-069 sessions...")

        cpe_use_cases.stop_tr069_client(cpe)

        print(
            f"✓ CPE {cpe_id} is unreachable for TR-069 sessions "
            "(cwmp_plugin stopped)"
        )

        context["cpe_was_taken_offline"] = True
        context["cpe_offline_timestamp"] = (
            datetime.now(timezone.utc).replace(tzinfo=None)
        )

        return context

    @keyword("Make CPE unreachable for TR-069")
    def make_cpe_unreachable_for_tr069(self, cpe: CPE) -> dict:
        """Alias for The CPE is unreachable for TR-069 sessions."""
        return self.make_unreachable_for_tr069(cpe)

    @keyword("The CPE comes online and connects to the ACS")
    def bring_online_and_connect(
        self, acs: ACS, cpe: CPE, cpe_id: str = None, offline_timestamp: Any = None, timeout: int = 120
    ) -> str:
        """Bring CPE back online and wait for ACS connection.

        Maps to scenario step:
        - "Then when the CPE comes online, it connects to the ACS"

        Arguments:
            acs: ACS device instance
            cpe: CPE device instance
            cpe_id: CPE identifier (optional)
            offline_timestamp: When CPE was taken offline (optional)
            timeout: Timeout in seconds (default: 120)

        Returns:
            Reconnection timestamp
        """
        if cpe_id is None:
            cpe_id = cpe.sw.cpe_id

        print(f"Bringing CPE {cpe_id} back online...")

        cpe_use_cases.start_tr069_client(cpe)
        print(f"✓ CPE {cpe_id} TR-069 client restarted")

        print(f"Waiting for CPE {cpe_id} to connect to ACS...")

        acs_use_cases.wait_for_inform_message(
            acs,
            cpe_id,
            event_codes=["1 BOOT"],
            since=offline_timestamp,
            timeout=timeout,
        )

        reconnection_timestamp = datetime.now(timezone.utc).replace(tzinfo=None)
        print(f"✓ CPE {cpe_id} reconnected to ACS")

        return str(reconnection_timestamp)

    @keyword("Bring CPE back online")
    def bring_cpe_back_online(
        self, acs: ACS, cpe: CPE, cpe_id: str = None, offline_timestamp: Any = None, timeout: int = 120
    ) -> str:
        """Alias for The CPE comes online and connects to the ACS."""
        return self.bring_online_and_connect(acs, cpe, cpe_id, offline_timestamp, timeout)

    # =========================================================================
    # Uptime Keywords
    # =========================================================================

    @keyword("Get CPE uptime")
    def get_uptime(self, cpe: CPE) -> float:
        """Get CPE uptime in seconds.

        Arguments:
            cpe: CPE device instance

        Returns:
            Uptime in seconds
        """
        return cpe_use_cases.get_console_uptime_seconds(cpe)

    @keyword("Get console uptime")
    def get_console_uptime(self, cpe: CPE) -> float:
        """Alias for Get CPE uptime."""
        return self.get_uptime(cpe)

    @keyword("Verify CPE rebooted")
    def verify_rebooted(self, cpe: CPE, initial_uptime: float) -> None:
        """Verify CPE has rebooted by checking uptime decreased.

        Arguments:
            cpe: CPE device instance
            initial_uptime: Initial uptime in seconds (before reboot)
        """
        current_uptime = cpe_use_cases.get_console_uptime_seconds(cpe)

        if current_uptime >= initial_uptime:
            raise AssertionError(
                f"CPE did not reboot: current uptime {current_uptime}s >= "
                f"initial uptime {initial_uptime}s"
            )

        print(
            f"✓ CPE rebooted. Uptime reset from {initial_uptime}s to {current_uptime}s"
        )

    # =========================================================================
    # Console Management Keywords
    # =========================================================================

    @keyword("Refresh CPE Console Connection")
    def refresh_console_connection(self, cpe: CPE) -> bool:
        """Refresh CPE console connection (disconnect + reconnect).

        This is aligned with the pytest cleanup behavior where console
        connections are always refreshed after each test.

        Arguments:
            cpe: CPE device instance

        Returns:
            True if console connection was refreshed successfully
        """
        print("↻ Refreshing CPE console connection...")
        if cpe_use_cases.refresh_console_connection(cpe):
            print("✓ Console connection refreshed successfully")
            return True
        else:
            print("⚠ Could not refresh console connection")
            return False

    @keyword("Disconnect CPE Console")
    def disconnect_console(self, cpe: CPE) -> None:
        """Disconnect from CPE console.

        Arguments:
            cpe: CPE device instance
        """
        print("Disconnecting from CPE console...")
        try:
            cpe.hw.disconnect_from_consoles()
            print("✓ Disconnected from CPE console")
        except Exception as e:
            print(f"⚠ Error disconnecting (may be expected): {e}")

    @keyword("Reconnect CPE Console")
    def reconnect_console(self, cpe: CPE) -> bool:
        """Reconnect to CPE console.

        Arguments:
            cpe: CPE device instance

        Returns:
            True if connection was successful
        """
        print("Reconnecting to CPE console...")
        try:
            device_name = getattr(cpe, "device_name", "cpe")
            cpe.hw.connect_to_consoles(device_name)
            print("✓ Reconnected to CPE console")
            return True
        except Exception as e:
            print(f"❌ Failed to reconnect to console: {e}")
            return False
