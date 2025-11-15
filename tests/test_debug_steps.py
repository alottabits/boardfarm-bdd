"""Test file for step-by-step debugging.

Use this file with debug-step-by-step.feature to test individual steps.
Edit the feature file to uncomment/comment steps as needed.
"""

from pathlib import Path

from pytest_bdd import scenarios

TESTS_DIR = Path(__file__).parent.absolute()
FEATURES_DIR = TESTS_DIR / "features"
DEBUG_FEATURE = FEATURES_DIR / "debug-step-by-step.feature"

scenarios(str(DEBUG_FEATURE.absolute()))

