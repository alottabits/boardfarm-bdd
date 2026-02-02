"""Base Boardfarm Keywords for Robot Framework.

Provides additional utility keywords that complement robotframework_boardfarm.BoardfarmLibrary.

NOTE: Device access keywords (Get Device By Type, Get Device Manager, etc.) are provided
by robotframework_boardfarm.BoardfarmLibrary. This library provides supplementary utilities.

Mirrors: Common functionality used across tests/step_defs/ files.
"""

import time
from datetime import datetime, timezone
from typing import Any

from robot.api.deco import keyword, library


@library(scope="SUITE", doc_format="TEXT")
class BoardfarmKeywords:
    """Supplementary keywords for Boardfarm tests.
    
    This library provides utility keywords that complement BoardfarmLibrary.
    For device access, use robotframework_boardfarm.BoardfarmLibrary.
    """

    def __init__(self) -> None:
        """Initialize BoardfarmKeywords."""
        self._extra_context: dict[str, Any] = {}

    # =========================================================================
    # Extra Context Management (supplement to BoardfarmLibrary)
    # =========================================================================

    @keyword("Context Has Key")
    def context_has_key(self, key: str) -> bool:
        """Check if a key exists in the extra context.

        Arguments:
            key: Context key name

        Returns:
            True if key exists, False otherwise
        """
        return key in self._extra_context

    @keyword("Store Extra Context")
    def store_extra_context(self, key: str, value: Any) -> None:
        """Store a value in the extra context (separate from BoardfarmLibrary context).

        Arguments:
            key: Context key name
            value: Value to store
        """
        self._extra_context[key] = value

    @keyword("Get Extra Context")
    def get_extra_context(self, key: str, default: Any = None) -> Any:
        """Retrieve a value from the extra context.

        Arguments:
            key: Context key name
            default: Default value if key not found

        Returns:
            Stored value or default
        """
        return self._extra_context.get(key, default)

    # =========================================================================
    # Utility Keywords
    # =========================================================================

    @keyword("Wait For Seconds")
    def wait_for_seconds(self, seconds: float | str) -> None:
        """Wait for specified number of seconds.

        Arguments:
            seconds: Number of seconds to wait
        """
        time.sleep(float(seconds))

    @keyword("Log Test Message")
    def log_test_message(self, message: str, level: str = "INFO") -> None:
        """Log a message with specified level.

        Arguments:
            message: Message to log
            level: Log level (INFO, DEBUG, WARN, ERROR)
        """
        from robot.api import logger
        logger.write(message, level)  # type: ignore[arg-type]

    @keyword("Get Current UTC Timestamp")
    def get_current_utc_timestamp(self) -> str:
        """Get current UTC timestamp.

        Returns:
            ISO format timestamp string
        """
        return datetime.now(timezone.utc).isoformat()

    @keyword("Get Timestamp For Filtering")
    def get_timestamp_for_filtering(self) -> datetime:
        """Get current UTC timestamp as datetime object for log filtering.

        Returns:
            datetime object (useful for passing to ACS/CPE keywords)
        """
        return datetime.now(timezone.utc).replace(tzinfo=None)
