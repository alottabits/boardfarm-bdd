"""Helper script to run pytest with coverage programmatically."""

import sys
from pathlib import Path
import coverage
import pytest

# Add project root to Python path to ensure modules are found
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Start coverage measurement
# We are interested in the step_defs module
cov = coverage.Coverage(source=["tests.step_defs"])
cov.start()

# Run pytest on the unit tests
pytest.main(["tests/unit/test_step_defs/"])

# Stop coverage and generate report
cov.stop()
cov.save()

# Print report to console
cov.report(show_missing=True)
