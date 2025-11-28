"""Mock Boardfarm context for unit testing."""

import datetime
from typing import Any, Optional


class MockContext:
    """Mock Boardfarm context for unit testing step definitions.
    
    This replaces the bf_context fixture in step definitions, providing
    a controllable mock for testing without requiring boardfarm infrastructure.
    """
    
    def __init__(self):
        # Phone references
        self.caller: Optional[Any] = None
        self.callee: Optional[Any] = None
        self.sipcenter: Optional[Any] = None
        
        # Device references by name (for testbed-like access)
        self.lan_phone: Optional[Any] = None
        self.wan_phone: Optional[Any] = None
        self.wan_phone2: Optional[Any] = None
        
        # Cleanup tracking
        self.original_config: dict = {}
        self.configured_phones: dict = {}
        
        # Timing
        self.scenario_start_time: Optional[datetime.datetime] = None
        
        # Additional context for scenarios
        self.call_immediately_disconnected: bool = False
        self.disconnect_reason: str = ""
        self.busy_maker: Optional[Any] = None
    
    def set_caller(self, phone: Any) -> None:
        """Set the caller phone."""
        self.caller = phone
    
    def set_callee(self, phone: Any) -> None:
        """Set the callee phone."""
        self.callee = phone
    
    def set_sipcenter(self, server: Any) -> None:
        """Set the SIP server."""
        self.sipcenter = server
