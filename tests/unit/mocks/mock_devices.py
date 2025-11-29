"""Mock device classes for unit testing step definitions."""

import datetime
from typing import Optional, Set

from boardfarm3.templates.sip_phone import SIPPhone


class MockConsole:
    """Mock console for device interactions."""
    
    def __init__(self):
        self.before = ""
        self.after = ""


class MockSIPPhone(SIPPhone):
    """Lightweight mock of SIPPhone for unit testing.
    
    This mock implements the same interface as PJSIPPhone but without
    any actual device interaction. All behavior is controllable via
    attributes for testing purposes.
    """
    
    def __init__(self, name: str = "mock_phone", number: str = "1000"):
        # Call parent constructor
        super().__init__()
        
        # Store name and number as private attributes (accessed via properties)
        self._name = name
        self._number = number
        self.phone_started = True
        
        # Internal state (can be controlled in tests)
        self._state = "idle"  # idle, ringing, dialing, connected
        self.last_dialed_number: Optional[str] = None
        
        # Control flags for simulating device behavior
        self._dial_should_succeed = True
        self._answer_should_succeed = True
        self._wait_for_state_result = True
        
        # Mock console for logging checks
        self._console = MockConsole()
    
    @property
    def name(self) -> str:
        """Get phone name."""
        return self._name
    
    @property
    def number(self) -> str:
        """Get phone number."""
        return self._number
    
    def is_idle(self) -> bool:
        """Check if phone is idle."""
        return self._state == "idle"
    
    def is_ringing(self) -> bool:
        """Check if phone is ringing."""
        return self._state == "ringing"
    
    def is_connected(self) -> bool:
        """Check if phone is connected."""
        return self._state == "connected"
    
    def is_dialing(self) -> bool:
        """Check if phone is dialing."""
        return self._state == "dialing"
    
    def is_playing_dialtone(self) -> bool:
        """Check if phone is playing dial tone."""
        return self.is_idle()
    
    def dial(self, number: str) -> None:
        """Dial a number."""
        if not self._dial_should_succeed:
            raise Exception("Dial failed")
        self._state = "dialing"
        self.last_dialed_number = number
    
    def answer(self) -> bool:
        """Answer incoming call."""
        if not self._answer_should_succeed:
            return False
        if self._state == "ringing":
            self._state = "connected"
            return True
        return False
    
    def hangup(self) -> None:
        """Hang up call."""
        self._state = "idle"
    
    def wait_for_state(self, expected_state: str, timeout: int = 10) -> bool:
        """Wait for phone to reach expected state."""
        # In mock, we either have the state or we don't (no actual waiting)
        # Can be controlled via _wait_for_state_result for testing
        if self._wait_for_state_result:
            return self._state == expected_state
        return False
    
    # --- Abstract method implementations required by SIPPhone base class ---
    
    def answer_waiting_call(self) -> bool:
        """Answer a waiting call."""
        return True
    
    def detect_dialtone(self) -> bool:
        """Detect if dial tone is present."""
        return self.is_playing_dialtone()
    
    def has_off_hook_warning(self) -> bool:
        """Check if phone has off-hook warning."""
        return False
    
    def hook_flash(self) -> None:
        """Perform hook flash."""
        pass
    
    @property
    def ipv4_addr(self) -> str:
        """Get IPv4 address."""
        return "192.168.1.10"
    
    @property
    def ipv6_addr(self) -> str:
        """Get IPv6 address."""
        return "::1"
    
    def is_call_ended(self) -> bool:
        """Check if call has ended."""
        return self._state == "idle"
    
    def is_call_not_answered(self) -> bool:
        """Check if call was not answered."""
        return False
    
    def is_call_waiting(self) -> bool:
        """Check if there's a call waiting."""
        return False
    
    def is_code_ended(self) -> bool:
        """Check if code has ended."""
        return False
    
    def is_in_conference(self) -> bool:
        """Check if phone is in a conference."""
        return False
    
    def is_incall_connected(self) -> bool:
        """Check if in-call is connected."""
        return self._state == "connected"
    
    def is_incall_dialing(self) -> bool:
        """Check if in-call is dialing."""
        return self._state == "dialing"
    
    def is_incall_playing_dialtone(self) -> bool:
        """Check if in-call is playing dial tone."""
        return self.is_playing_dialtone()
    
    def is_line_busy(self) -> bool:
        """Check if line is busy."""
        return self._state == "busy"
    
    def is_onhold(self) -> bool:
        """Check if call is on hold."""
        return False
    
    def merge_two_calls(self) -> None:
        """Merge two calls into conference."""
        pass
    
    def off_hook(self) -> None:
        """Take phone off hook."""
        if self._state == "idle":
            self._state = "dialing"
    
    def on_hook(self) -> None:
        """Put phone on hook."""
        self._state = "idle"
    
    def phone_config(self, **kwargs) -> None:
        """Configure phone with parameters.
        
        Args:
            **kwargs: Configuration parameters (ipv6_flag, sipserver_fqdn, etc.)
        """
        # Mock implementation - just store the config
        self._config = kwargs
    
    def phone_kill(self) -> None:
        """Kill phone process."""
        self.phone_started = False
    
    def phone_start(self) -> None:
        """Start phone process."""
        self.phone_started = True
    
    def place_call_offhold(self) -> None:
        """Take call off hold."""
        pass
    
    def place_call_onhold(self) -> None:
        """Place call on hold."""
        pass
    
    def press_R_button(self) -> None:
        """Press R button."""
        pass
    
    def press_buttons(self, buttons: str) -> None:
        """Press buttons on phone."""
        pass
    
    def reject_waiting_call(self) -> None:
        """Reject a waiting call."""
        pass
    
    def reply_with_code(self, code: str) -> None:
        """Reply with SIP code."""
        pass
    
    def toggle_call(self) -> None:
        """Toggle between calls."""
        pass


class MockSIPServer:
    """Lightweight mock of SIPServer for unit testing."""
    
    def __init__(self, ipv4_addr: str = "192.168.1.100", ipv6_addr: str = "::1"):
        self.ipv4_addr = ipv4_addr
        self.ipv6_addr = ipv6_addr
        self._registered_users: Set[str] = set()
        self._active_calls = 0
        self._status = "Running"
    
    def get_all_users(self) -> Set[str]:
        """Get all registered users."""
        return self._registered_users
    
    def get_status(self) -> str:
        """Get server status."""
        return self._status
    
    def register_user(self, number: str) -> None:
        """Register a user (for test setup)."""
        self._registered_users.add(number)
    
    def unregister_user(self, number: str) -> None:
        """Unregister a user (for test setup)."""
        self._registered_users.discard(number)
    
    def get_active_calls(self) -> int:
        """Get number of active calls."""
        return self._active_calls
    
    def set_active_calls(self, count: int) -> None:
        """Set active calls count (for test setup)."""
        self._active_calls = count
    
    def verify_sip_message(
        self, message_type: str, since: Optional[datetime.datetime] = None, timeout: int = 5
    ) -> bool:
        """Verify SIP message in logs."""
        # Mock implementation - can be controlled in tests
        return True
    
    def get_rtpengine_stats(self) -> dict:
        """Get RTPEngine statistics."""
        return {"engaged": False, "sessions": 0}


class MockCPE:
    """Lightweight mock of CPE device for unit testing."""
    
    def __init__(self):
        self.name = "mock_cpe"
        self.device_name = "cpe"
        
        # Mock hardware/software interfaces
        self.hw = MockCPEHardware()
        self.sw = MockCPESoftware()


class MockCPEHardware:
    """Mock CPE hardware interface."""
    
    def connect_to_consoles(self, device_name: str) -> None:
        """Mock console connection."""
        pass
    
    def disconnect_from_consoles(self) -> None:
        """Mock console disconnection."""
        pass


class MockCPESoftware:
    """Mock CPE software interface."""
    
    def __init__(self):
        self.cpe_id = "mock_cpe_001"


class MockACS:
    """Lightweight mock of ACS (GenieACS) for unit testing."""
    
    def __init__(self):
        self.name = "mock_acs"
    
    def GPV(self, param: str, cpe_id: str, timeout: int = 60) -> str:
        """Mock Get Parameter Value."""
        return "mock_value"
    
    def SPV(self, params: list, cpe_id: str, timeout: int = 60) -> int:
        """Mock Set Parameter Value."""
        return 0  # Success


class MockDevices:
    """Mock devices namespace (like boardfarm devices fixture)."""
    
    def __init__(self):
        # Create default mock devices
        self.lan_phone = MockSIPPhone(name="lan_phone", number="1000")
        self.wan_phone = MockSIPPhone(name="wan_phone", number="2000")
        self.wan_phone2 = MockSIPPhone(name="wan_phone2", number="3000")
        self.sipcenter = MockSIPServer()
        self.cpe = MockCPE()
        self.acs = MockACS()
