"""Base Boardfarm Keywords for Robot Framework.

Provides device access and common utilities. This library works with
the BoardfarmListener to access deployed devices.

Mirrors: Common functionality used across tests/step_defs/ files.
"""

from typing import Any

from robot.api.deco import keyword

from robotframework_boardfarm.listener import get_listener


class BoardfarmKeywords:
    """Base keywords for Boardfarm device access and testbed utilities."""

    ROBOT_LIBRARY_SCOPE = "SUITE"
    ROBOT_LIBRARY_DOC_FORMAT = "TEXT"

    def __init__(self) -> None:
        """Initialize BoardfarmKeywords."""
        self._context: dict[str, Any] = {}

    # =========================================================================
    # Device Access Keywords
    # =========================================================================

    @keyword("Get device by type")
    @keyword("Get ${device_type} device")
    def get_device_by_type(self, device_type: str, index: int = 0) -> Any:
        """Get a device by its type.

        Maps to scenario steps:
        - "Get device by type"
        - "Get ACS device" / "Get CPE device" / etc.

        Arguments:
            device_type: Type of device (e.g., "CPE", "ACS", "SIPPhone")
            index: Index if multiple devices of same type (default: 0)

        Returns:
            Device instance
        """
        listener = get_listener()
        return listener.device_manager.get_device_by_type(device_type, index)

    @keyword("Get Boardfarm config")
    def get_boardfarm_config(self) -> Any:
        """Get the Boardfarm configuration.

        Returns:
            BoardfarmConfig instance
        """
        listener = get_listener()
        return listener.boardfarm_config

    @keyword("Get device manager")
    def get_device_manager(self) -> Any:
        """Get the Boardfarm device manager.

        Returns:
            DeviceManager instance
        """
        listener = get_listener()
        return listener.device_manager

    # =========================================================================
    # Context Management Keywords
    # =========================================================================

    @keyword("Set test context")
    @keyword("Store in context")
    def set_context(self, key: str, value: Any) -> None:
        """Store a value in the test context.

        Maps to scenario steps:
        - "Set test context"
        - "Store in context"

        Arguments:
            key: Context key name
            value: Value to store
        """
        self._context[key] = value

    @keyword("Get test context")
    @keyword("Get from context")
    def get_context(self, key: str, default: Any = None) -> Any:
        """Retrieve a value from the test context.

        Maps to scenario steps:
        - "Get test context"
        - "Get from context"

        Arguments:
            key: Context key name
            default: Default value if key not found

        Returns:
            Stored value or default
        """
        return self._context.get(key, default)

    @keyword("Context has key")
    def has_context(self, key: str) -> bool:
        """Check if a key exists in the test context.

        Arguments:
            key: Context key name

        Returns:
            True if key exists, False otherwise
        """
        return key in self._context

    @keyword("Clear test context")
    def clear_context(self) -> None:
        """Clear all values from the test context."""
        self._context.clear()

    # =========================================================================
    # Utility Keywords
    # =========================================================================

    @keyword("Wait for seconds")
    @keyword("Sleep ${seconds} seconds")
    def wait_seconds(self, seconds: float) -> None:
        """Wait for specified number of seconds.

        Arguments:
            seconds: Number of seconds to wait
        """
        import time
        time.sleep(seconds)

    @keyword("Log message")
    def log_message(self, message: str, level: str = "INFO") -> None:
        """Log a message.

        Arguments:
            message: Message to log
            level: Log level (INFO, DEBUG, WARN, ERROR)
        """
        from robot.api import logger
        logger.write(message, level)

    @keyword("Get current timestamp")
    def get_timestamp(self) -> str:
        """Get current UTC timestamp.

        Returns:
            ISO format timestamp string
        """
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat()
