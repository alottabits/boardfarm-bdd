"""Test file to execute all BDD scenarios from feature files.

This script discovers all `.feature` files in the features directory
and loads their scenarios using pytest-bdd's scenarios() function.

Usage:
    pytest tests/execution/test-all-scenarios.py                    # Run all scenarios
    pytest tests/execution/test-all-scenarios.py -v                  # Verbose output
    pytest tests/execution/test-all-scenarios.py -k "UC-12345"      # Run specific tagged scenarios
    pytest tests/execution/test-all-scenarios.py --tb=short          # Shorter traceback format
"""

from pathlib import Path

import pytest
from pytest_bdd import scenarios

# Get the directory where this file is located (tests/execution/)
EXECUTION_DIR = Path(__file__).parent

# Get the features directory (go up one level to tests/, then into features/)
FEATURES_DIR = EXECUTION_DIR.parent / "features"

# Discover all .feature files
FEATURE_FILES = []
if FEATURES_DIR.exists():
    FEATURE_FILES.extend(FEATURES_DIR.glob("*.feature"))
    # Sort for consistent test ordering
    FEATURE_FILES.sort()

# Convert to absolute paths for pytest-bdd
FEATURE_PATHS = [str(f.absolute()) for f in FEATURE_FILES]

if not FEATURE_PATHS:
    pytest.skip(
        f"No feature files found in {FEATURES_DIR}. "
        "Please ensure .feature files exist in the features directory.",
        allow_module_level=True,
    )

# Load all scenarios from all feature files
# pytest-bdd's scenarios() function will create test functions for each scenario
# Each scenario will be executed as a separate pytest test
scenarios(*FEATURE_PATHS)

