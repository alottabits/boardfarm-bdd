"""Test file to execute all BDD scenarios from feature files.

Step definitions are automatically discovered and registered by conftest.py
at the project root, so no manual imports are needed here.
"""

from pathlib import Path

from pytest_bdd import scenarios

TESTS_DIR = Path(__file__).parent
FEATURES_DIR = TESTS_DIR / "features"

FEATURE_PATHS = [str(f.absolute()) for f in FEATURES_DIR.glob("*.feature")]

scenarios(*FEATURE_PATHS)
