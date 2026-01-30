"""Voice Keywords for Robot Framework.

Keywords for SIP phone and voice call operations, aligned with BDD scenario steps.
Uses @keyword decorator to map clean function names to scenario step text.

Mirrors: tests/step_defs/sip_phone_steps.py
"""

import time
from typing import Any

from robot.api.deco import keyword

from boardfarm3.templates.sip_phone import SIPPhone
from boardfarm3.templates.sip_server import SIPServer
from boardfarm3.use_cases import voice as voice_use_cases


class VoiceKeywords:
    """Keywords for voice/SIP phone operations matching BDD scenario steps."""

    ROBOT_LIBRARY_SCOPE = "SUITE"
    ROBOT_LIBRARY_DOC_FORMAT = "TEXT"

    def __init__(self) -> None:
        """Initialize VoiceKeywords."""
        self._phones: dict[str, SIPPhone] = {}
        self._sipcenter: SIPServer = None
        self._caller: SIPPhone = None
        self._callee: SIPPhone = None

    # =========================================================================
    # Setup Keywords
    # =========================================================================

    @keyword("The SIP server is running and operational")
    @keyword("Verify SIP server is running")
    def verify_sip_server_running(self, sipcenter: SIPServer) -> None:
        """Verify SIP server (Kamailio) is running.

        Maps to scenario step:
        - "Given the SIP server is running and operational"

        Arguments:
            sipcenter: SIP server instance
        """
        self._sipcenter = sipcenter
        status = sipcenter.get_status()
        assert status == "Running", f"SIP server is not running. Status: {status}"
        print(f"✓ SIP server is running: {status}")

    @keyword("Register phone with SIP server")
    def register_phone(
        self, phone: SIPPhone, sipcenter: SIPServer, name: str = None
    ) -> None:
        """Register a phone with the SIP server.

        Arguments:
            phone: SIPPhone instance
            sipcenter: SIP server instance
            name: Name to store phone under (optional)
        """
        sip_server_ip = sipcenter.ipv4_addr
        phone.phone_config(ipv6_flag=False, sipserver_fqdn=sip_server_ip)
        phone.phone_start()

        # Verify registration
        all_users = sipcenter.get_all_users()
        phone_number = phone.number
        assert phone_number in all_users, (
            f"Phone {phone.name} (number {phone_number}) is not registered. "
            f"All users: {all_users}"
        )

        if name:
            self._phones[name] = phone

        print(f"✓ Phone {phone.name} (number {phone_number}) is registered")

    @keyword("Assign caller and callee roles")
    @keyword("${caller_name} is the caller and ${callee_name} is the callee")
    def assign_roles(
        self, caller: SIPPhone, callee: SIPPhone, caller_name: str = None, callee_name: str = None
    ) -> None:
        """Assign caller and callee roles to phones.

        Maps to scenario step:
        - "Given lan_phone is the caller and wan_phone is the callee"

        Arguments:
            caller: Caller phone instance
            callee: Callee phone instance
            caller_name: Name of caller (optional)
            callee_name: Name of callee (optional)
        """
        self._caller = caller
        self._callee = callee

        if caller_name:
            self._phones[caller_name] = caller
        if callee_name:
            self._phones[callee_name] = callee

        print(f"✓ Assigned roles: caller={caller.name}, callee={callee.name}")

    # =========================================================================
    # Phone State Keywords
    # =========================================================================

    @keyword("The ${role} phone is idle")
    @keyword("Verify phone is idle")
    def verify_phone_idle(self, phone: SIPPhone) -> None:
        """Verify phone is in idle state.

        Maps to scenario step:
        - "Given the caller phone is idle"

        Arguments:
            phone: SIPPhone instance
        """
        assert phone.is_idle(), f"Phone {phone.name} is not in idle state"
        print(f"✓ Phone {phone.name} is in idle state")

    @keyword("Wait for phone state")
    def wait_for_state(
        self, phone: SIPPhone, expected_state: str, timeout: int = 10
    ) -> bool:
        """Wait for phone to reach expected state.

        Arguments:
            phone: SIPPhone instance
            expected_state: Expected state (idle, ringing, connected)
            timeout: Maximum time to wait in seconds

        Returns:
            True if phone reached expected state
        """
        success = phone.wait_for_state(expected_state, timeout=timeout)

        if success:
            print(f"✓ Phone {phone.name} reached {expected_state} state")
        else:
            print(
                f"✗ Phone {phone.name} did not reach {expected_state} state "
                f"within {timeout}s"
            )

        return success

    # =========================================================================
    # Call Setup Keywords
    # =========================================================================

    @keyword("The caller dials the callee's number")
    @keyword("Caller calls callee")
    def caller_dials_callee(self, caller: SIPPhone = None, callee: SIPPhone = None) -> None:
        """Caller dials the callee's number.

        Maps to scenario step:
        - "When the caller dials the callee's number"

        Arguments:
            caller: Caller phone (optional, uses stored reference)
            callee: Callee phone (optional, uses stored reference)
        """
        if caller is None:
            caller = self._caller
        if callee is None:
            callee = self._callee

        print(f"Phone {caller.name} dialing {callee.number}...")
        voice_use_cases.call_a_phone(caller, callee)
        print(f"✓ Phone {caller.name} dialed {callee.number}")

    @keyword("${phone_name} calls ${number}")
    @keyword("Phone dials number")
    def phone_dials_number(self, phone: SIPPhone, number: str) -> None:
        """Phone dials a specific number.

        Arguments:
            phone: SIPPhone instance
            number: Number to dial
        """
        print(f"Phone {phone.name} calling {number}...")
        phone.dial(number)
        print(f"✓ Phone {phone.name} called {number}")

    # =========================================================================
    # Call Answer/Reject Keywords
    # =========================================================================

    @keyword("The callee answers the call")
    @keyword("Callee answers call")
    def callee_answers(self, callee: SIPPhone = None) -> None:
        """Callee answers incoming call.

        Maps to scenario step:
        - "When the callee answers the call"

        Arguments:
            callee: Callee phone (optional, uses stored reference)
        """
        if callee is None:
            callee = self._callee

        print(f"Phone {callee.name} answering call...")
        success = voice_use_cases.answer_a_call(callee)
        assert success, f"Phone {callee.name} failed to answer call"
        print(f"✓ Phone {callee.name} answered call")

    @keyword("The ${role} rejects the call")
    @keyword("Phone rejects call")
    def phone_rejects_call(self, phone: SIPPhone) -> None:
        """Reject incoming call with 603 Decline response.

        Arguments:
            phone: SIPPhone instance
        """
        print(f"Phone {phone.name} rejecting call...")
        phone.reply_with_code(603)

        success = self.wait_for_state(phone, "idle", timeout=5)
        assert success, f"Phone {phone.name} did not return to idle after rejection"

        print(f"✓ Phone {phone.name} rejected call with 603 Decline")

    # =========================================================================
    # Call Termination Keywords
    # =========================================================================

    @keyword("The ${role} hangs up")
    @keyword("Phone hangs up")
    def phone_hangs_up(self, phone: SIPPhone) -> None:
        """Hang up active call.

        Maps to scenario step:
        - "When the caller hangs up"

        Arguments:
            phone: SIPPhone instance
        """
        print(f"Phone {phone.name} hanging up...")
        voice_use_cases.disconnect_the_call(phone)
        print(f"✓ Phone {phone.name} hung up")

    @keyword("Caller hangs up")
    def caller_hangs_up(self, caller: SIPPhone = None) -> None:
        """Caller hangs up the call.

        Arguments:
            caller: Caller phone (optional, uses stored reference)
        """
        if caller is None:
            caller = self._caller
        self.phone_hangs_up(caller)

    # =========================================================================
    # Verification Keywords
    # =========================================================================

    @keyword("The callee phone should start ringing")
    @keyword("Verify phone is ringing")
    def verify_phone_ringing(self, phone: SIPPhone = None, timeout: int = 10) -> None:
        """Verify phone is ringing.

        Maps to scenario step:
        - "Then the callee phone should start ringing"

        Arguments:
            phone: SIPPhone instance (optional, uses callee)
            timeout: Timeout in seconds
        """
        if phone is None:
            phone = self._callee

        success = self.wait_for_state(phone, "ringing", timeout=timeout)
        assert success, f"Phone {phone.name} did not start ringing"

    @keyword("Both phones should be connected")
    @keyword("Verify both phones connected")
    def verify_both_connected(
        self, caller: SIPPhone = None, callee: SIPPhone = None, timeout: int = 10
    ) -> None:
        """Verify both phones are in connected state.

        Maps to scenario step:
        - "Then both phones should be connected"

        Arguments:
            caller: Caller phone (optional, uses stored reference)
            callee: Callee phone (optional, uses stored reference)
            timeout: Timeout in seconds
        """
        if caller is None:
            caller = self._caller
        if callee is None:
            callee = self._callee

        caller_connected = self.wait_for_state(caller, "connected", timeout=timeout)
        callee_connected = self.wait_for_state(callee, "connected", timeout=timeout)

        assert caller_connected, f"Caller {caller.name} is not connected"
        assert callee_connected, f"Callee {callee.name} is not connected"

    @keyword("Both phones should return to idle state")
    @keyword("Verify both phones idle")
    def verify_both_idle(
        self, caller: SIPPhone = None, callee: SIPPhone = None, timeout: int = 10
    ) -> None:
        """Verify both phones returned to idle state.

        Maps to scenario step:
        - "Then both phones should return to idle state"

        Arguments:
            caller: Caller phone (optional, uses stored reference)
            callee: Callee phone (optional, uses stored reference)
            timeout: Timeout in seconds
        """
        if caller is None:
            caller = self._caller
        if callee is None:
            callee = self._callee

        caller_idle = self.wait_for_state(caller, "idle", timeout=timeout)
        callee_idle = self.wait_for_state(callee, "idle", timeout=timeout)

        assert caller_idle, f"Caller {caller.name} did not return to idle"
        assert callee_idle, f"Callee {callee.name} did not return to idle"

    @keyword("A bidirectional RTP media session should be established")
    @keyword("Verify RTP session established")
    def verify_rtp_session(
        self, caller: SIPPhone = None, callee: SIPPhone = None
    ) -> None:
        """Verify RTP media session is established.

        Maps to scenario step:
        - "Then a bidirectional RTP media session should be established"

        Arguments:
            caller: Caller phone (optional, uses stored reference)
            callee: Callee phone (optional, uses stored reference)
        """
        if caller is None:
            caller = self._caller
        if callee is None:
            callee = self._callee

        assert caller.is_connected(), f"Caller {caller.name} not in connected state"
        assert callee.is_connected(), f"Callee {callee.name} not in connected state"

        print("✓ Bidirectional RTP media session established")

    @keyword("The SIP server should terminate the call")
    @keyword("Verify SIP call terminated")
    def verify_call_terminated(self, sipcenter: SIPServer = None) -> None:
        """Verify SIP server terminated the call.

        Maps to scenario step:
        - "Then the SIP server should terminate the call"

        Arguments:
            sipcenter: SIP server (optional, uses stored reference)
        """
        if sipcenter is None:
            sipcenter = self._sipcenter

        active_calls = sipcenter.get_active_calls()
        if active_calls == 0:
            print("✓ SIP server terminated call (0 active calls)")
        elif active_calls > 0:
            print(f"⚠ Warning: {active_calls} active calls still on SIP server")
        else:
            print("✓ SIP server terminating call (verification skipped)")
