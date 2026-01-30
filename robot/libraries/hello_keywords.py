"""Hello Keywords for Robot Framework.

Simple keywords for smoke tests and basic verification.
Uses @keyword decorator to map clean function names to scenario step text.

Mirrors: tests/step_defs/hello_steps.py
"""

from robot.api.deco import keyword


class HelloKeywords:
    """Keywords for simple smoke tests and basic verification."""

    ROBOT_LIBRARY_SCOPE = "SUITE"
    ROBOT_LIBRARY_DOC_FORMAT = "TEXT"

    @keyword("I say hello")
    @keyword("Say hello")
    def say_hello(self) -> None:
        """A simple step that prints a message and passes.

        Maps to scenario step:
        - "When I say hello"
        """
        print("Hello, BDD World!")

    @keyword("Hello world test")
    def hello_world(self) -> str:
        """Simple hello world test.

        Returns:
            Hello world message
        """
        message = "Hello, Robot Framework BDD World!"
        print(message)
        return message

    @keyword("Verify basic connectivity")
    def verify_connectivity(self) -> None:
        """Verify basic test framework connectivity.

        This is a smoke test to ensure the test framework is working.
        """
        print("✓ Test framework is connected and operational")

    @keyword("Log test message")
    def log_test_message(self, message: str) -> None:
        """Log a test message.

        Arguments:
            message: Message to log
        """
        print(f"Test message: {message}")
