"""Test file to execute the main firmware upgrade scenario only."""

from pathlib import Path
from pytest_bdd import scenarios

# Import step definitions locally to ensure they are loaded correctly.
from tests.step_defs import (  # noqa: F401
    acs_steps,
    background_steps,
    cpe_config_steps,
    firmware_steps,
    provisioning_steps,
    verification_steps,
)

TESTS_DIR = Path(__file__).parent
FEATURES_DIR = TESTS_DIR / "features"
FEATURE_FILE = FEATURES_DIR / "CPE Firmware Upgrade.feature"

scenarios(str(FEATURE_FILE.absolute()))
