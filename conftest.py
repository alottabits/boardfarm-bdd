"""Root conftest.py - delegates to tests/ directory.

This file allows running pytest from the project root while keeping
all pytest-bdd artifacts in the tests/ subdirectory.
"""

import sys
from pathlib import Path

# Add tests directory to path so imports work correctly
tests_dir = Path(__file__).parent / "tests"
if str(tests_dir) not in sys.path:
    sys.path.insert(0, str(tests_dir))

# Re-export all fixtures from tests/conftest.py
# This makes them available when running from the project root
from tests.conftest import *  # noqa: F401, F403
