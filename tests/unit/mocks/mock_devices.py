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
        
        self.name = name
        self.number = number
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
