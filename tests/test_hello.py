"""
Test runner for 'hello.feature', using the @when decorator
and a separate, imported step definition file.

Step definitions are imported and registered in conftest.py (at project root).
"""

from pathlib import Path

from pytest_bdd import scenarios

# Use absolute path to the feature file
TESTS_DIR = Path(__file__).parent.absolute()
FEATURE_FILE = TESTS_DIR / "features" / "hello.feature"

scenarios(str(FEATURE_FILE.absolute()))
